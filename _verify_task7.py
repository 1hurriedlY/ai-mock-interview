"""任务 7 验证脚本：面试路由（start / roles / chat SSE / end）。

- roles：不依赖大模型，纯校验
- start：真实调用题卡 Agent（需 DashScope key），用固定岗位/角色
- chat：打桩 InterviewerAgent.decide，走 SSE 流式，校验事件流
- end：幂等结束 + 消息落库校验

运行：.venv/Scripts/python.exe _verify_task7.py
"""
import json
import sys

sys.path.insert(0, "backend")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------- 准备一个用户 ----------
USER = {"username": "task7_user", "password": "secret123"}
client.post("/api/auth/register", json=USER)  # 已存在则 409，可忽略
r = client.post("/api/auth/login", json=USER)
assert r.status_code == 200, r.text
TOKEN = r.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("[0] 登录成功，token:", TOKEN[:20], "...")

# ---------- 1. roles ----------
r = client.get("/api/interview/roles", headers=HEADERS)
assert r.status_code == 200, r.text
roles = r.json()
print("[1] 角色列表:", [(x["key"], x["name"]) for x in roles])
assert {x["key"] for x in roles} == {"technical", "HR", "stress"}
assert all(x.get("name") and x.get("description") for x in roles)

# ---------- 2. start（真实调题卡 Agent） ----------
r = client.post(
    "/api/interview/start",
    headers=HEADERS,
    json={"job_title": "Python 后端开发", "role": "technical"},
)
print("[2] start:", r.status_code)
assert r.status_code == 200, r.text
body = r.json()
session_id = body["session_id"]
print("    session_id:", session_id)
print("    开场白:", body["opening"][:50], "...")
assert body["stage"] == "opening"
assert body["opening"]

# 错误角色
r = client.post(
    "/api/interview/start",
    headers=HEADERS,
    json={"job_title": "x", "role": "bad_role"},
)
assert r.status_code == 400, r.text
print("[3] 非法角色 → 400 通过")

# ---------- 3. chat SSE（打桩面试官） ----------
from unittest.mock import patch

from app.services.agents import pipeline as pipe_mod

fake_decisions = iter([
    {"action": "next", "reply": "自我介绍不错，我们进入基础题。请解释什么是线程与进程的区别。", "reference": "进程/线程概念、区别、适用场景"},
    {"action": "probe", "reply": "请再展开讲讲你项目里的并发实践。", "reference": "并发实践细节"},
    {"action": "finish", "reply": "面试到这里就结束了，感谢参与。", "reference": "结束语"},
])


def fake_decide(**kwargs):
    return next(fake_decisions)


with patch.object(pipe_mod.InterviewerAgent, "decide", side_effect=fake_decide):
    r = client.post(
        f"/api/interview/{session_id}/chat",
        headers=HEADERS,
        json={"message": "我叫小明，三年 Python 后端经验。"},
    )
    print("[4] chat 状态码:", r.status_code)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream"), r.headers
    text = r.text
    print("    SSE 前 200 字符:", text[:200])
    # 事件流应包含 message 增量与 done 事件
    assert "event: message" in text, text
    assert "event: done" in text, text
    done_line = [l for l in text.splitlines() if l.startswith("data: {")][-1]
    done = json.loads(done_line[6:])
    print("    done:", {k: v for k, v in done.items() if k != "reference"})
    assert done["action"] == "next"
    assert done["stage"] in ("basic", "opening")
    assert done["finished"] is False
    assert done["reply"]

    # 第二轮：probe
    r = client.post(
        f"/api/interview/{session_id}/chat",
        headers=HEADERS,
        json={"message": "我们项目里用了多进程处理 CPU 密集任务。"},
    )
    done = json.loads([l for l in r.text.splitlines() if l.startswith("data: {")][-1][6:])
    assert done["action"] == "probe", done
    print("[5] 第二轮 probe 通过")

    # 第三轮：finish → finished=True
    r = client.post(
        f"/api/interview/{session_id}/chat",
        headers=HEADERS,
        json={"message": "没有更多了，谢谢。"},
    )
    done = json.loads([l for l in r.text.splitlines() if l.startswith("data: {")][-1][6:])
    assert done["action"] == "finish", done
    assert done["finished"] is True, done
    print("[6] 第三轮 finish 通过，finished=True")

# ---------- 4. 消息落库校验 ----------
from app.database import SessionLocal
from app.models import ChatMessage

db = SessionLocal()
try:
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id).all()
    roles = [m.role for m in msgs]
    print("[7] 落库消息角色序列:", roles)
    assert roles.count("user") == 3 and roles.count("assistant") == 4, roles  # 开场白 + 3 轮
    refs = [m.reference for m in msgs if m.reference]
    assert refs, "参考要点未落库"
    print("    参考要点样例:", refs[-1])
finally:
    db.close()

# ---------- 5. end 幂等 + 状态 ----------
r = client.post(f"/api/interview/{session_id}/end", headers=HEADERS, json={})
assert r.status_code == 200, r.text
r1 = r.json()
print("[8] end 第一次:", r1["status"], "message_count:", r1["message_count"])
assert r1["status"] == "completed"
assert r1["already_completed"] is False

r = client.post(
    f"/api/interview/{session_id}/end",
    headers=HEADERS,
    json={"expression_seq": [{"time": 0, "expression": "happy", "confidence": 0.9}]},
)
r2 = r.json()
assert r2["already_completed"] is True, r2
assert r2["expression_count"] == 1, r2
print("[9] end 幂等 + 表情参数 通过")

# 已结束会话再 chat 应 400
r = client.post(
    f"/api/interview/{session_id}/chat",
    headers=HEADERS,
    json={"message": "还能聊吗"},
)
assert r.status_code == 400, r.text
print("[10] 已结束会话再 chat → 400 通过")

# ---------- 6. 越权访问 ----------
from app.auth import create_access_token

client.post("/api/auth/register", json={"username": "task7_other", "password": "secret123"})
r = client.post("/api/auth/login", json={"username": "task7_other", "password": "secret123"})
other_token = r.json()["access_token"]
r = client.post(
    f"/api/interview/{session_id}/chat",
    headers={"Authorization": f"Bearer {other_token}"},
    json={"message": "越权"},
)
assert r.status_code == 403, r.text
print("[11] 越权访问 → 403 通过")

print("== 任务 7 验证全部通过 ==")
