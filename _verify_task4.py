"""任务 4 验证脚本：面试题生成 Agent（真实调用通义千问）。"""
import sys

sys.path.insert(0, "backend")

from app.services.agents.question_agent import QuestionAgent
from app.config import STAGES

agent = QuestionAgent()

# 1. 无简历、技术面
print("[1] 生成技术面题卡（无简历）...")
card1 = agent.generate_card(job_title="Python 后端工程师", role="technical")
stages = card1["stages"]
print("    阶段键:", list(stages.keys()))
assert set(stages.keys()) == set(STAGES), f"阶段不齐: {list(stages.keys())}"
opening = stages["opening"]
print("    opening 题数:", len(opening))
assert isinstance(opening, list) and len(opening) >= 1
print("    opening 题目:", opening[0].get("question", "")[:40])
for s in ("basic", "deep", "stress", "closing"):
    qs = stages[s]
    print(f"    {s}: {len(qs)} 题")
    assert isinstance(qs, list) and len(qs) >= 1, f"{s} 阶段无题"
    # 每道题都应有 question 和 reference
    for q in qs:
        assert q.get("question"), f"{s} 阶段题目为空"
        assert q.get("reference"), f"{s} 阶段缺少参考要点"

# 2. 带简历画像、HR 面
print("[2] 生成 HR 面题卡（带简历）...")
resume = {
    "skills": ["Python", "FastAPI", "MySQL", "Redis", "Docker"],
    "projects": [{"name": "在线商城系统", "description": "负责订单模块与支付回调"}],
    "highlights": ["日订单量 2 万"],
    "education": "本科",
}
card2 = agent.generate_card(job_title="Python 后端工程师", role="HR", resume_analysis=resume)
assert set(card2["stages"].keys()) == set(STAGES)
print("    HR 面 basic 题数:", len(card2["stages"]["basic"]))
print("    HR 面 basic 第一题:", card2["stages"]["basic"][0].get("question", "")[:40])

print("== 任务 4 验证全部通过 ==")
