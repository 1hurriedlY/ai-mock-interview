import _utf8_bootstrap # noqa: F401
import json
import sys
sys.path.insert(0, "backend")
from app.services.agents.scoring_agent import ScoringAgent
from app.services.agents.base import parse_json_object

a = ScoringAgent()
#不走 normalize，看 chat_json原始返回
raw = a.chat_json(
 """你是资深面试官与职业评估专家。基于以下面试记录输出评估报告 JSON。
【目标岗位】Python后端开发
【面试官角色】technical
【面试对话记录】
面试官：请自我介绍
候选人：我三年 Python后端经验，做过支付系统
面试官：讲讲支付幂等怎么设计的
候选人：用了唯一键 +状态机，数据库唯一约束兜底
请输出评估报告 JSON。""",
 temperature=0.4,
)
print("keys:", list(raw.keys()))
print("summary:", repr(raw.get("summary", "<无>")))
print(json.dumps(raw, ensure_ascii=False, indent=2)[:800])
