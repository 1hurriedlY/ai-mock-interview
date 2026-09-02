"""任务 9 验证脚本：评分 Agent + 报告落库 + /end 接入评分。

- 离线部分：ScoringAgent._normalize 兜底规范化（不调大模型）
- 真实部分：真实调用评分 Agent 生成报告（需 DashScope key），走 /end 落库

运行：.venv/Scripts/python.exe _verify_task9.py
"""
import _utf8_bootstrap  # noqa: F401
import json
import sys

sys.path.insert(0, "backend")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------- 0. 离线验证 _normalize 兜底 ----------
from app.services.agents.scoring_agent import ScoringAgent

norm = ScoringAgent._normalize(
    {
        "summary": "还不错",
        "overall_score": 82,
        "dimensions": {"专业技能": 80, "沟通表达": 90, "逻辑思维": 75, "项目经验": 70, "岗位匹配": 85},
        "match_analysis": {"match_level": "高", "reason": "契合", "strengths": ["基础扎实"], "gaps": ["缺架构经验"]},
        "suggestions": ["多读源码"],
        "expression_analysis": {"comment": "整体自信", "highlights": ["微笑频率高"]},
    },
    expression_seq=[{"time": 1, "expression": "happy", "confidence": 0.9}],
)
assert norm["overall_score"] == 82
assert norm["dimensions"]["沟通表达"] == 90
assert norm["match_analysis"]["match_level"] == "高"
assert norm["expression_analysis"]["comment"] == "整体自信"
print("[0] _normalize 兜底规范化通过")

# 缺字段 + 空表情 → 默认值
norm2 = ScoringAgent._normalize({}, expression_seq=None)
assert norm2["overall_score"] == 0
assert norm2["dimensions"] == {"专业技能": 0, "沟通表达": 0, "逻辑思维": 0, "项目经验": 0, "岗位匹配": 0}
assert norm2["expression_analysis"] == {}
print("[1] 缺字段兜底（空表情 → 无表情分析）通过")

# ---------- 1. 造一场带对话的面试 ----------
USER = {"username": "task9_user", "password": "secret123"}
client.post("/api/auth/register", json=USER)
r = client.post("/api/auth/login", json=USER)
assert r.status_code == 200, r.text
TOKEN = r.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

r = client.post(
    "/api/interview/start",
    headers=HEADERS,
    json={"job_title": "Python 后端开发", "role": "technical"},
)
assert r.status_code == 200, r.text
sess_id = r.json()["session_id"]
print("[2] 造面试会话:", sess_id)

# 直接往 Redis/MySQL 灌几条对话（模拟已进行的面试）
from app.database import SessionLocal
from app.models import ChatMessage

conversation = [
    {"role": "assistant", "content": "请自我介绍"},
    {"role": "user", "content": "我三年 Python 后端经验，做过支付系统"},
    {"role": "assistant", "content": "讲讲支付幂等怎么设计的"},
    {"role": "user", "content": "用了唯一键 + 状态机，数据库唯一约束兜底"},
]
from app.redis_client import redis_client

redis_client.set_session_context(sess_id, conversation)

db = SessionLocal()
try:
    for m in conversation:
        db.add(ChatMessage(session_id=sess_id, role=m["role"], content=m["content"]))
    db.commit()
finally:
    db.close()

# ---------- 2. /end 真实调用评分 Agent ----------
r = client.post(
    f"/api/interview/{sess_id}/end",
    headers=HEADERS,
    json={"expression_seq": [
        {"time": 0, "expression": "happy", "confidence": 0.8},
        {"time": 3, "expression": "neutral", "confidence": 0.6},
    ]},
)
print("[3] /end 状态码:", r.status_code)
assert r.status_code == 200, r.text
body = r.json()
print("    报告分:", body["report"]["overall_score"], "| report_id:", body["report_id"])
assert body["report_id"], "report_id 未返回"
assert body["status"] == "completed"
rep = body["report"]
print("    评语:", rep["summary"][:60])
print("    五维:", rep["dimensions"])
assert rep["overall_score"] > 0, "评分应为正数"
assert set(rep["dimensions"].keys()) == {"专业技能", "沟通表达", "逻辑思维", "项目经验", "岗位匹配"}
assert rep["match_analysis"]["match_level"] in ("高", "中", "低", "未知")
assert isinstance(rep["suggestions"], list) and len(rep["suggestions"]) > 0
assert rep["expression_analysis"].get("comment"), "表情点评缺失"
print("[4] 报告结构完整（五维/匹配/建议/表情点评）通过")

# ---------- 3. 幂等：再次 end 返回同一报告，不重复调用 ----------
r2 = client.post(f"/api/interview/{sess_id}/end", headers=HEADERS, json={})
assert r2.status_code == 200, r2.text
body2 = r2.json()
assert body2["already_completed"] is True
assert body2["report_id"] == body["report_id"], "幂等失败：报告 id 不一致"
print("[5] /end 幂等（同一 report_id）通过")

# ---------- 4. 落库校验 ----------
db = SessionLocal()
try:
    from app.models import InterviewReport

    stored = db.query(InterviewReport).filter(InterviewReport.session_id == sess_id).first()
    assert stored is not None
    assert stored.overall_score == rep["overall_score"]
    assert json.loads(stored.expression_analysis)["comment"]
    print("[6] 报告已落库 interview_reports 通过")
finally:
    db.close()

# ---------- 5. 历史详情能看到报告 ----------
r = client.get(f"/api/history/{sess_id}", headers=HEADERS)
assert r.status_code == 200, r.text
detail = r.json()
assert detail["report"] and detail["report"]["overall_score"] == rep["overall_score"]
assert detail["report"]["expression_analysis"]["comment"]
print("[7] 历史详情返回完整报告通过")

print("== 任务 9 验证全部通过 ==")
