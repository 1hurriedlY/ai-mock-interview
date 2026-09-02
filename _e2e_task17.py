# -*- coding: utf-8 -*-
"""任务17 E2E 收尾验证：注册→start→SSE 对话→end(带表情时间轴)→报告 timeline→导出→历史回看。

与 _e2e_task14.py 相比，重点验证 v3 视觉链路：
1. end 携带乱序/带 no_face 的表情序列
2. 报告 expression_analysis.timeline 是"归一化后的原始序列"（非模型生成）
3. 历史详情同样返回 timeline → 前端报告页/导出都能渲染
4. DOCX/PDF 导出文件头正确
"""
import io
import json
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8000"
USERNAME = f"e2e17_{int(time.time())}"
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


def api(method, path, body=None, token=None):
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    resp = urllib.request.urlopen(req, timeout=300)
    return json.loads(resp.read().decode("utf-8"))


def stream_send(session_id, message, token):
    """POST SSE chat，解析事件，返回 done payload。"""
    payload = json.dumps({"message": message}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + f"/api/interview/{session_id}/chat",
        data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
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
        parts = text.split("\n\n")
        buf = parts[-1].encode("utf-8")
        for part in parts[:-1]:
            ev = parse_sse(part)
            if ev:
                events.append(ev)
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
    print(f"任务17 E2E：用户={USERNAME} 岗位={JOB_TITLE} 角色={ROLE}")
    print("=" * 60)

    # ---------- 1 注册 / 登录 ----------
    print("\n[1] 认证")
    r = api("POST", "/api/auth/register", {"username": USERNAME, "password": PASSWORD})
    token = r["access_token"]
    check("注册返回 token", bool(token))
    me = api("GET", "/api/auth/me", token=token)
    check("me 返回用户名", me.get("username") == USERNAME)

    # ---------- 2 开始面试 ----------
    print("\n[2] 开始面试")
    t0 = time.time()
    start = api("POST", "/api/interview/start",
                {"job_title": JOB_TITLE, "role": ROLE}, token=token)
    sid = start["session_id"]
    check("start 返回 session_id", sid > 0, f"session={sid} 耗时{time.time()-t0:.1f}s")
    check("start 有开场白", len(start.get("opening", "")) > 20)
    check("start stage=opening", start.get("stage") == "opening")

    # ---------- 3 短对话（4 轮左右即可让评分有料） ----------
    print("\n[3] 流式对话")
    answers = [
        "我叫小王，3 年 Python 后端经验，用过 FastAPI、Flask、Django，做过电商订单系统。",
        "最熟 FastAPI + SQLAlchemy 2.0 + MySQL，会 pydantic 做数据校验。",
        "高并发优化做过，用 Redis 缓存 + 异步接口，把下单接口从 300ms 优化到 80ms。",
        "线上踩过慢查询的坑，用 explain 分析加联合索引解决。",
    ]
    last_stage = "opening"
    finished = False
    for i, msg in enumerate(answers):
        done, _ = stream_send(sid, msg, token)
        if done is None:
            check(f"第{i+1}轮返回 done", False)
            break
        reply = done.get("reply") or ""
        stage = done.get("stage", last_stage)
        last_stage = stage
        print(f"    轮{i+1} action={done.get('action')} stage={stage} 字数={len(reply)}")
        check(f"第{i+1}轮 done.reply 非空", bool(reply))
        if done.get("finished"):
            finished = True
            break
    check("面试推进或结束", finished or last_stage != "opening", f"finished={finished} last_stage={last_stage}")

    # ---------- 4 结束面试：携带乱序 + no_face + 非法 time 的表情序列 ----------
    print("\n[4] 结束面试（表情时间轴 v3 链路）")
    expr_seq = [
        {"time": 40, "expression": "happy", "confidence": 0.91},   # 乱序
        {"time": 3, "expression": "neutral", "confidence": 0.6},
        {"time": 25, "expression": "no_face", "confidence": 0.0},  # 无人脸断点 → 应被过滤
        {"time": 12, "expression": "fearful", "confidence": 0.7},
        {"time": 3.7, "expression": "happy", "confidence": 0.9},   # 浮点 time → int 3
        {"time": "abc", "expression": "angry", "confidence": 0.5}, # 非法 time → 剔除
    ]
    end = api("POST", f"/api/interview/{sid}/end", {"expression_seq": expr_seq}, token=token)
    rep = end.get("report") or {}
    check("end 返回 report", bool(rep), f"score={rep.get('overall_score')}")
    check("总分 0-100", 0 <= rep.get("overall_score", -1) <= 100)
    dims = rep.get("dimensions") or {}
    check("五维完整", len(dims) == 5, str(list(dims.keys())))
    check("报告含 expression_analysis", bool(rep.get("expression_analysis")))

    ea = rep.get("expression_analysis") or {}
    tl = ea.get("timeline")
    check("expression_analysis.timeline 存在", isinstance(tl, list), f"len={len(tl) if isinstance(tl,list) else 'N/A'}")
    # 归一化断言：4 条（40/3/12/3.7→3 条 + 25 no_face 滤 + abc 滤 = 4 条：3,3,12,40）
    # 其中 3 出现两次（time=3 和 3.7→3），需排序；预期 [{3,neutral},{3,happy},{12,fearful},{40,happy}]
    expect_cnt = 4
    check("timeline 条数正确（滤 no_face+非法time）", len(tl) == expect_cnt, f"实际={len(tl)} {str(tl)[:120]}")
    times = [t["time"] for t in tl]
    check("timeline 按 time 升序", times == sorted(times), str(times))
    check("timeline 无 no_face", all(t["expression"] != "no_face" for t in tl))
    check("timeline time 均为 int", all(isinstance(t["time"], int) for t in tl), str(times))
    conf_ok = all(0 <= t["confidence"] <= 1 for t in tl)
    check("timeline confidence 0-1", conf_ok)
    check("expression_analysis.comment 存在(表情点评)", bool(ea.get("comment")), str(ea.get("comment"))[:40])
    check("expression_analysis.highlights 非空", bool(ea.get("highlights")), str(ea.get("highlights"))[:40])

    # ---------- 5 导出 DOCX / PDF ----------
    print("\n[5] 导出")
    rid = rep["id"]
    for fmt in ("docx", "pdf"):
        info = api("POST", f"/api/report/{rid}/export?format={fmt}", {}, token=token)
        check(f"导出{fmt}成功", info.get("format") == fmt and info.get("size", 0) > 0,
              f"{info.get('filename')} {info.get('size')}B")
        req = urllib.request.Request(
            BASE + f"/api/report/{rid}/download?format={fmt}",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = urllib.request.urlopen(req, timeout=60).read()
        ok_head = data[:5] == b"%PDF-" if fmt == "pdf" else data[:4] == b"PK\x03\x04"
        check(f"{fmt}文件头正确", ok_head, str(data[:8]))

    # ---------- 6 历史回看：详情返回 timeline ----------
    print("\n[6] 历史回看")
    lst = api("GET", "/api/history", token=token)
    mine = [s for s in lst if s["id"] == sid]
    check("历史列表含本会话", len(mine) == 1, f"共{len(lst)}场")
    det = api("GET", f"/api/history/{sid}", token=token)
    check("详情 status=completed", det["status"] == "completed")
    check("详情含报告", bool(det["report"]))
    det_ea = (det["report"] or {}).get("expression_analysis") or {}
    det_tl = det_ea.get("timeline")
    check("历史详情 timeline 与报告一致", det_tl == tl, f"len={len(det_tl) if isinstance(det_tl,list) else 'N/A'}")
    check("历史消息含参考要点", sum(1 for m in det["messages"] if m.get("reference")) >= 1)

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print(f"结果：PASS {len(passed)} / FAIL {len(failed)}（共{len(passed)+len(failed)}项）")
    if failed:
        print("失败项：", failed)
        sys.exit(1)
    print("任务17 E2E 全绿 ✅")
    sys.exit(0)


if __name__ == "__main__":
    main()
