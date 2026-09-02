"""任务 11 验证脚本：项目渠道/话术 Agent + 路由 + 入库 + 历史。

- 离线部分：_normalize 兜底规范化（不调大模型）
- 真实部分：真实调用 ProjectAgent 生成渠道清单 + STAR 话术，走路由落库，历史可查

运行：.venv/Scripts/python.exe _verify_task11.py
"""
import _utf8_bootstrap  # noqa: F401
import json
import sys

sys.path.insert(0, "backend")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------- 0. 离线验证 _normalize 兜底 ----------
from app.services.agents.project_agent import ProjectAgent

norm_c = ProjectAgent._normalize_channels(
    {
        "summary": "渠道总览",
        "categories": [
            {"category": "全职招聘", "items": [{"name": "BOSS直聘", "free": True, "suitable": "1-3年", "description": "直接沟通"}]}
        ],
    }
)
assert norm_c["summary"] == "渠道总览"
assert norm_c["categories"][0]["items"][0]["name"] == "BOSS直聘"
assert norm_c["categories"][0]["items"][0]["free"] is True

# 空结构兜底
norm_c2 = ProjectAgent._normalize_channels({})
assert norm_c2["categories"] == []
print("[0] channels _normalize 通过")

norm_s = ProjectAgent._normalize_script(
    {
        "project_name": "支付系统",
        "summary": "电梯介绍",
        "star": {"situation": "背景", "task": "任务", "action": "行动", "result": "结果"},
        "deep_dive": [{"question": "追问", "answer": "应对"}],
        "pitfalls": [{"issue": "坑", "lesson": "复盘"}],
        "script": "完整话术",
    },
    project_name="支付系统",
)
assert norm_s["star"]["situation"] == "背景"
assert norm_s["deep_dive"][0]["answer"] == "应对"
assert norm_s["script"] == "完整话术"

# 缺 star/script → 兜底
norm_s2 = ProjectAgent._normalize_script({}, project_name="X系统")
assert norm_s2["star"] == {"situation": "", "task": "", "action": "", "result": ""}
assert norm_s2["script"] == "（X系统 的完整话术未生成，请重新生成。）"
print("[1] script _normalize 通过")

# ---------- 1. 注册登录 ----------
USER = {"username": "task11_user", "password": "secret123"}
client.post("/api/auth/register", json=USER)
r = client.post("/api/auth/login", json=USER)
assert r.status_code == 200, r.text
TOKEN = r.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("[2] 登录成功")

# ---------- 2. 渠道清单 ----------
r = client.post("/api/project/channels", headers=HEADERS)
print("[3] /project/channels 状态码:", r.status_code)
assert r.status_code == 200, r.text
body = r.json()
channels_id = body["id"]
content = body["content"]
cats = content.get("categories") or []
total_items = sum(len(c.get("items") or []) for c in cats)
print("    总览:", content.get("summary", "")[:60])
print("    分类数:", len(cats), "| 平台总数:", total_items)
assert content.get("summary"), "渠道总览缺失"
assert len(cats) >= 3, "应有三类渠道"
assert total_items >= 6, "平台数不足"
print("[4] 渠道清单结构完整通过")

# ---------- 3. STAR 话术 ----------
r = client.post(
    "/api/project/script",
    headers=HEADERS,
    json={"project_name": "电商秒杀系统", "description": "Redis 预扣库存 + MQ 削峰"},
)
print("[5] /project/script 状态码:", r.status_code)
assert r.status_code == 200, r.text
body = r.json()
script_id = body["id"]
sc = body["content"]
print("    项目名:", sc.get("project_name"))
print("    电梯介绍:", sc.get("summary", "")[:60])
print("    追问数:", len(sc.get("deep_dive") or []), "| 踩坑数:", len(sc.get("pitfalls") or []))
assert sc.get("project_name")
assert sc.get("summary"), "电梯介绍缺失"
assert all(sc.get("star", {}).get(k) for k in ("situation", "task", "action", "result")), "STAR 缺项"
assert sc.get("script"), "完整话术缺失"
print("[6] STAR 话术结构完整通过")

# ---------- 4. 落库校验 ----------
from app.database import SessionLocal

db = SessionLocal()
try:
    from app.models import ProjectReport

    c_stored = db.get(ProjectReport, channels_id)
    assert c_stored is not None and c_stored.type == "channels"
    s_stored = db.get(ProjectReport, script_id)
    assert s_stored is not None and s_stored.type == "script"
    assert s_stored.project_name == sc.get("project_name")
    assert json.loads(s_stored.content)["summary"] == sc["summary"]
    print("[7] 报告已落库 project_reports（channels/script）通过")
finally:
    db.close()

# ---------- 5. 历史列表与详情 ----------
r = client.get("/api/project/history", headers=HEADERS)
assert r.status_code == 200, r.text
items = r.json()
assert len(items) >= 2
assert any(i["type"] == "channels" for i in items)
assert any(i["type"] == "script" and i["project_name"] for i in items)
print("[8] 历史列表返回通过")

r = client.get(f"/api/project/history/{script_id}", headers=HEADERS)
assert r.status_code == 200, r.text
assert r.json()["content"]["script"] == sc["script"]
print("[9] 历史详情返回完整话术通过")

# 越权
USER2 = {"username": "task11_user2", "password": "secret123"}
client.post("/api/auth/register", json=USER2)
r = client.post("/api/auth/login", json=USER2)
TOKEN2 = r.json()["access_token"]
r = client.get(f"/api/project/history/{script_id}", headers={"Authorization": f"Bearer {TOKEN2}"})
assert r.status_code == 403, r.text
print("[10] 越权访问拦截通过")

# 空项目名校验（strip 后为空 → 400）
r = client.post("/api/project/script", headers=HEADERS, json={"project_name": "   "})
assert r.status_code == 400, r.text
print("[11] 空项目名校验通过")

print("== 任务 11 验证全部通过 ==")
