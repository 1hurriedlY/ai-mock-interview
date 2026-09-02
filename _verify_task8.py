"""任务 8 验证脚本：历史路由（列表 / 详情 / 越权 / 报告解析）。

利用任务 7 已经产生的会话数据（task7_user 的 session 1），
再补造一个已结束 + 有报告的会话，验证报告 JSON 字段解析。

运行：.venv/Scripts/python.exe _verify_task8.py
"""
import _utf8_bootstrap  # noqa: F401  强制 UTF-8 输出，避免 Windows 终端乱码
import json
import sys

sys.path.insert(0, "backend")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

USER = {"username": "task8_user", "password": "secret123"}
client.post("/api/auth/register", json=USER)
r = client.post("/api/auth/login", json=USER)
assert r.status_code == 200, r.text
TOKEN = r.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("[0] 登录 task8_user 成功")

# ---------- 造数据：一场已结束 + 有报告的会话 ----------
r = client.post(
    "/api/interview/start",
    headers=HEADERS,
    json={"job_title": "前端工程师", "role": "HR"},
)
assert r.status_code == 200, r.text
sess_id = r.json()["session_id"]
print("[1] 造会话:", sess_id)

# 直接落一条消息 + 一份报告（模拟评分 Agent 产出）
from datetime import datetime

from app.database import SessionLocal
from app.models import ChatMessage, InterviewReport, InterviewSession

db = SessionLocal()
try:
    db.add(ChatMessage(session_id=sess_id, role="user", content="我做了三年 React。"))
    db.add(ChatMessage(
        session_id=sess_id, role="assistant",
        content="很好，讲讲你的组件设计。", reference="组件设计要点",
    ))
    db.add(InterviewReport(
        session_id=sess_id,
        summary="候选人沟通表达流畅，技术基础扎实。",
        overall_score=78,
        dimensions=json.dumps(
            {"专业技能": 75, "沟通表达": 85, "逻辑思维": 80, "项目经验": 70, "岗位匹配": 78},
            ensure_ascii=False,
        ),
        match_analysis=json.dumps({"match_level": "较高", "reason": "技术栈匹配"}, ensure_ascii=False),
        suggestions=json.dumps(["加强项目深挖", "补充性能优化经验"], ensure_ascii=False),
        expression_analysis=json.dumps(
            {"timeline": [{"time": 0, "expression": "happy", "confidence": 0.8}], "comment": "整体轻松自信"},
            ensure_ascii=False,
        ),
    ))
    # 标记已结束
    sess = db.get(InterviewSession, sess_id)
    sess.status = "completed"
    sess.ended_at = datetime.now()
    db.commit()
finally:
    db.close()

# ---------- 1. 列表 ----------
r = client.get("/api/history", headers=HEADERS)
assert r.status_code == 200, r.text
items = r.json()
print("[2] 列表条数:", len(items), "（task8_user 应有 >= 1 条）")
assert len(items) >= 1
first = items[0]
print("    最新会话:", first["job_title"], first["interviewer_name"], first["status"],
      "| 消息数:", first["message_count"], "| 报告分:", first["report"]["overall_score"] if first["report"] else None)
# 按时间倒序
times = [x["created_at"] for x in items]
assert times == sorted(times, reverse=True), "列表未按时间倒序"
assert first["message_count"] >= 2
assert first["report"] and first["report"]["overall_score"] == 78
assert first["interviewer_name"] == "HR 行为面"
print("[3] 列表排序 + 报告概要 + 角色中文名 通过")

# ---------- 2. 详情 ----------
r = client.get(f"/api/history/{sess_id}", headers=HEADERS)
assert r.status_code == 200, r.text
detail = r.json()
print("[4] 详情:", detail["job_title"], "| 状态:", detail["status"], "| 消息数:", len(detail["messages"]))
assert detail["status"] == "completed"
assert len(detail["messages"]) >= 3  # 开场白 + 2 条
roles = [m["role"] for m in detail["messages"]]
assert "user" in roles and "assistant" in roles
refs = [m["reference"] for m in detail["messages"] if m.get("reference")]
assert "组件设计要点" in refs, refs
print("[5] 消息含 reference 通过:", refs)

rep = detail["report"]
assert rep and rep["overall_score"] == 78
assert isinstance(rep["dimensions"], dict) and rep["dimensions"]["沟通表达"] == 85
assert rep["match_analysis"]["match_level"] == "较高"
assert isinstance(rep["suggestions"], list) and len(rep["suggestions"]) == 2
assert rep["expression_analysis"]["comment"] == "整体轻松自信"
print("[6] 报告 JSON 字段解析通过（五维/匹配/建议/表情）")

# 不存在的会话 → 404
r = client.get("/api/history/999999", headers=HEADERS)
assert r.status_code == 404, r.text
print("[7] 不存在会话 → 404 通过")

# 越权：另一个用户看不到
client.post("/api/auth/register", json={"username": "task8_other", "password": "secret123"})
r = client.post("/api/auth/login", json={"username": "task8_other", "password": "secret123"})
other_token = r.json()["access_token"]
r = client.get(
    f"/api/history/{sess_id}",
    headers={"Authorization": f"Bearer {other_token}"},
)
assert r.status_code == 403, r.text
print("[8] 越权访问详情 → 403 通过")

print("== 任务 8 验证全部通过 ==")
