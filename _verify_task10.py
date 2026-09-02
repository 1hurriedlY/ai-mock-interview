"""任务 10 验证脚本：行业调研 Agent + 路由 + 入库 + 历史。

- 离线部分：IndustryAgent._normalize 兜底规范化（不调大模型）
- 真实部分：真实调用行业调研 Agent 生成报告，走 /research 落库，历史可查

运行：.venv/Scripts/python.exe _verify_task10.py
"""
import _utf8_bootstrap  # noqa: F401
import json
import sys

sys.path.insert(0, "backend")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------- 0. 离线验证 _normalize 兜底 ----------
from app.services.agents.industry_agent import IndustryAgent

norm = IndustryAgent._normalize(
    {
        "overview": "概述",
        "industry_chain": [{"name": "上游", "description": "原料"}],
        "key_players": [{"name": "A公司", "type": "头部", "description": "龙头"}],
        "business_models": [{"name": "订阅", "description": "月费"}],
        "trends": ["智能化"],
        "job_skills": [{"skill": "Python", "level": "必须", "description": "用"}],
        "interview_questions": [{"question": "Q1", "angle": "考察逻辑"}],
    },
    industry_name="工业软件",
)
assert norm["industry"] == "工业软件"
assert norm["industry_chain"][0]["name"] == "上游"
assert norm["job_skills"][0]["level"] == "必须"
assert norm["interview_questions"][0]["angle"] == "考察逻辑"
print("[0] _normalize 兜底规范化通过")

# 空字段 / 缺键 → 默认值
norm2 = IndustryAgent._normalize({}, industry_name="储能")
assert norm2["industry"] == "储能"
assert norm2["overview"] == "「储能」是当前一个值得关注的行业方向。"
assert norm2["industry_chain"] == []
assert norm2["key_players"] == []
assert norm2["job_skills"] == []
print("[1] 缺字段兜底通过")

# ---------- 1. 注册登录 ----------
USER = {"username": "task10_user", "password": "secret123"}
client.post("/api/auth/register", json=USER)
r = client.post("/api/auth/login", json=USER)
assert r.status_code == 200, r.text
TOKEN = r.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("[2] 登录成功")

# 未带 token 应 401
r = client.post("/api/industry/research", json={"industry_name": "储能"})
assert r.status_code == 401, r.text
print("[3] 未认证拦截通过")

# ---------- 2. 真实调研 ----------
r = client.post(
    "/api/industry/research",
    headers=HEADERS,
    json={"industry_name": "储能"},
)
print("[4] /research 状态码:", r.status_code)
assert r.status_code == 200, r.text
body = r.json()
report_id = body["id"]
content = body["content"]
print("    行业:", body["industry_name"])
print("    概览:", content.get("overview", "")[:60])
print("    产业链环节数:", len(content.get("industry_chain") or []))
print("    头部玩家数:", len(content.get("key_players") or []))
print("    趋势条数:", len(content.get("trends") or []))
print("    技能条数:", len(content.get("job_skills") or []))
print("    面试题数:", len(content.get("interview_questions") or []))

assert content.get("overview"), "overview 缺失"
assert len(content.get("industry_chain") or []) >= 2, "产业链环节不足"
assert len(content.get("key_players") or []) >= 3, "头部玩家不足"
assert len(content.get("trends") or []) >= 1
assert len(content.get("job_skills") or []) >= 1
assert len(content.get("interview_questions") or []) >= 1
print("[5] 报告结构完整通过")

# ---------- 3. 落库校验 ----------
db_session = __import__("app.database", fromlist=["SessionLocal"]).SessionLocal()
try:
    from app.models import IndustryReport

    stored = db_session.get(IndustryReport, report_id)
    assert stored is not None
    assert stored.industry_name == body["industry_name"]
    assert json.loads(stored.content)["overview"] == content["overview"]
    print("[6] 报告已落库 industry_reports 通过")
finally:
    db_session.close()

# ---------- 4. 历史列表与详情 ----------
r = client.get("/api/industry/history", headers=HEADERS)
assert r.status_code == 200, r.text
items = r.json()
assert len(items) >= 1
assert items[0]["industry_name"] == body["industry_name"]
assert items[0]["overview"]
print("[7] 历史列表返回通过")

r = client.get(f"/api/industry/history/{report_id}", headers=HEADERS)
assert r.status_code == 200, r.text
detail = r.json()
assert detail["content"]["industry_chain"] == content["industry_chain"]
print("[8] 历史详情返回完整报告通过")

# 越权访问：其他用户看不到
USER2 = {"username": "task10_user2", "password": "secret123"}
client.post("/api/auth/register", json=USER2)
r = client.post("/api/auth/login", json=USER2)
TOKEN2 = r.json()["access_token"]
r = client.get(f"/api/industry/history/{report_id}", headers={"Authorization": f"Bearer {TOKEN2}"})
assert r.status_code == 403, r.text
print("[9] 越权访问拦截通过")

print("== 任务 10 验证全部通过 ==")
