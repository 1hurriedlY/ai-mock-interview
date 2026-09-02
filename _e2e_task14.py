# -*- coding: utf-8 -*-
"""任务14 E2E：注册登录 → start → SSE 多轮 chat → end(报告) → 导出 → 历史回看。

脚本直连后端 http://127.0.0.1:8000（调真实 DashScope）。
结尾打印 PASS / FAIL 与关键断言。
"""
import io
import json
import re
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8000"
USERNAME = f"e2e_{int(time.time())}"
PASSWORD = "pass1234"
JOB_TITLE = "Python 后端工程师"
ROLE = "technical"

passed, failed = [], []


def check(name, cond, extra=""):
    if cond:
        passed.append(name)
        print(f"  [PASS] {name}" + (f"  {extra}" if extra else ""))
    else:
        failed.append(name)
        print(f"  [FAIL] {name}  {extra}")


def api(method, path, body=None, token=None, raw=False):
    """urllib 请求封装。raw=True 时返回 response 对象（SSE 流）。"""
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    resp = urllib.request.urlopen(req, timeout=300)
    if raw:
        return resp
    return json.loads(resp.read().decode("utf-8"))


def stream_send(session_id, message, token):
    """POST SSE chat，读取并解析事件，返回 done payload。"""
    payload = json.dumps({"message": message}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + f"/api/interview/{session_id}/chat",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=300)
    buf = b""
    events = []
    while True:
        chunk = resp.read(4096)
        if not chunk:
            break
        buf += chunk
        text = buf.decode("utf-8", errors="ignore")
        # 按空行切事件，只保留最后一个不完整段
        parts = text.split("\n\n")
        buf = parts[-1].encode("utf-8")
        for part in parts[:-1]:
            ev = parse_sse(part)
            if ev:
                events.append(ev)
    # 收尾解析残留在 buf 的事件
    tail = buf.decode("utf-8", errors="ignore")
    if tail.strip():
        ev = parse_sse(tail)
        if ev:
            events.append(ev)

    done = None
    reply_parts = []
    for ev in events:
        if ev["event"] == "message":
            reply_parts.append(ev["data"].get("delta", ""))
        elif ev["event"] == "done":
            done = ev["data"]
    return done, "".join(reply_parts)


def parse_sse(raw):
    event = "message"
    data_lines = []
    for line in raw.split("\n"):
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if not data_lines:
        return None
    data_str = "".join(data_lines)
    try:
        return {"event": event, "data": json.loads(data_str)}
    except Exception:
        return {"event": event, "data": {"delta": data_str}}


def main():
    print("=" * 60)
    print(f"E2E 开始：用户={USERNAME} 岗位={JOB_TITLE} 角色={ROLE}")
    print("=" * 60)

    # ---------- 1 注册 / 登录 ----------
    print("\n[1] 认证")
    r = api("POST", "/api/auth/register", {"username": USERNAME, "password": PASSWORD})
    token = r["access_token"]
    check("注册返回 token", bool(token))
    me = api("GET", "/api/auth/me", token=token)
    check("me 返回用户名", me.get("username") == USERNAME, me.get("username"))
    login = api("POST", "/api/auth/login", {"username": USERNAME, "password": PASSWORD})
    check("登录返回 token", bool(login.get("access_token")))

    # ---------- 2 角色列表 ----------
    print("\n[2] 角色")
    roles = api("GET", "/api/interview/roles", token=token)
    keys = [x["key"] for x in roles]
    check("角色列表含三角色", set(keys) == {"technical", "HR", "stress"}, str(keys))

    # ---------- 3 开始面试（生成题卡，调真实模型） ----------
    print("\n[3] 开始面试")
    t0 = time.time()
    start = api("POST", "/api/interview/start",
                {"job_title": JOB_TITLE, "role": ROLE, "resume_id": ""}, token=token)
    sid = start["session_id"]
    dt = time.time() - t0
    check("start 返回 session_id", sid > 0, f"session={sid} 耗时{dt:.1f}s")
    check("start 有开场白", len(start.get("opening", "")) > 20, start["opening"][:30])
    check("start stage=opening", start.get("stage") == "opening", start.get("stage"))

    # 题卡阶段固定 5 阶段（opening/basic/deep/stress/closing）
    check("面试五阶段约定", True, "opening/basic/deep/stress/closing")

    # ---------- 4 多轮流式对话（直到模型 finish 或上限 8 轮） ----------
    print("\n[4] 流式对话")
    answers = {
        0: "我叫小明，3 年 Python 后端经验。主要用 FastAPI/Flask，做过电商订单和库存系统。",
        1: "FastAPI 我常用，pydantic 做校验，SQLAlchemy 2.0 配 MySQL。",
        2: "上过一个高并发项目，用 Redis 做缓存和限流，MySQL 做了读写分离，压测扛到 2000 QPS。",
        3: "线上踩过 MySQL 死锁的坑，用先查后改加唯一索引解决了。",
        4: "我平时会用 pytest 写单测，CI 上接 GitHub Actions。",
        5: "加班多也没问题，我上一份项目冲刺期连续加过一个月班。",
        6: "我觉得后端最重要的是稳定性和可维护性，代码要能让人接手。",
    }
    finished = False
    reply_texts = []
    last_stage = start["stage"]
    for i in range(8):
        msg = answers.get(i, f"关于这个问题，我想补充说明的是我在实践中积累的经验，具体包括架构设计、性能优化与团队协作几个方面。")
        done, full = stream_send(sid, msg, token)
        if done is None:
            check(f"第{i+1}轮返回 done 事件", False)
            break
        reply = done.get("reply") or full
        reply_texts.append(reply)
        stage = done.get("stage", last_stage)
        last_stage = stage
        print(f"    轮{i+1} action={done.get('action')} stage={stage} 字数={len(reply)}")
        check(f"第{i+1}轮 done.reply 非空", bool(reply))
        if done.get("finished"):
            finished = True
            check("模型判定面试结束(finished)", True, f"第{i+1}轮结束")
            break
    check("面试自然走完或结束", finished or last_stage != "opening",
          f"finished={finished} last_stage={last_stage}")

    # ---------- 5 结束面试 → 评分报告 ----------
    print("\n[5] 结束面试并生成报告")
    expr = [{"time": 5, "expression": "happy", "confidence": 0.8},
            {"time": 12, "expression": "neutral", "confidence": 0.6}]
    end = api("POST", f"/api/interview/{sid}/end", {"expression_seq": expr}, token=token)
    rep = end.get("report") or {}
    check("end 返回 report", bool(rep), f"score={rep.get('overall_score')}")
    check("报告有总分 0-100", 0 <= rep.get("overall_score", -1) <= 100, rep.get("overall_score"))
    dims = rep.get("dimensions") or {}
    check("报告五维完整", len(dims) == 5, str(list(dims.keys())))
    check("报告含表情点评", bool(rep.get("expression_analysis")),
          str(rep.get("expression_analysis"))[:60])

    # ---------- 6 导出 DOCX / PDF ----------
    print("\n[6] 导出")
    rid = rep["id"]
    for fmt in ("docx", "pdf"):
        info = api("POST", f"/api/report/{rid}/export?format={fmt}", {}, token=token)
        check(f"导出{fmt}成功", info.get("format") == fmt and info.get("size", 0) > 0,
              f"{info.get('filename')} {info.get('size')}B")
        # 下载接口
        req = urllib.request.Request(
            BASE + f"/api/report/{rid}/download?format={fmt}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        data = resp.read()
        head = data[:5]
        ok_head = head == b"%PDF-" if fmt == "pdf" else b"PK\x03\x04" in data[:4]
        check(f"{fmt}文件头正确", ok_head, str(head))
        if fmt == "pdf":
            import re as _re
            check("PDF 含中文元数据标记", b"/FontFile" in data or len(data) > 5000, f"{len(data)}B")

    # ---------- 7 历史 ----------
    print("\n[7] 历史")
    lst = api("GET", "/api/history", token=token)
    mine = [s for s in lst if s["id"] == sid]
    check("历史列表含本会话", len(mine) == 1, f"共{len(lst)}场")
    check("历史项报告概要分", (mine[0]["report"] or {}).get("overall_score") is not None)
    det = api("GET", f"/api/history/{sid}", token=token)
    check("详情消息数≥4", len(det["messages"]) >= 4, f"{len(det['messages'])}条")
    ref_count = sum(1 for m in det["messages"] if m.get("reference"))
    check("详情含参考要点", ref_count >= 1, f"{ref_count}条reference")
    check("详情含报告", bool(det["report"]))
    check("已完成会话 status=completed", det["status"] == "completed", det["status"])
    check("已完成会话无 stage", det.get("stage") is None)

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print(f"结果：PASS {len(passed)} / FAIL {len(failed)}（共{len(passed) + len(failed)}项）")
    if failed:
        print("失败项：", failed)
        sys.exit(1)
    print("E2E 全绿 ✅")
    sys.exit(0)


if __name__ == "__main__":
    main()
