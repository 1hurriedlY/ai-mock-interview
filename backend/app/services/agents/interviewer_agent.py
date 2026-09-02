"""面试官 Agent：模拟真实面试官推进对话。

职责：
- 依据候选人回答质量决策下一步动作：
  - next：回答充分 → 简短肯定，并自然地问出下一道题
  - probe：回答过短/含糊 → 请对方展开说明
  - followup：有可深挖的点但不够透 → 顺着回答追加一个追问
  - finish：最后一道题且回答充分 → 收尾结束语
- 跑题/过长回答会礼貌打断并拉回主题；每次只问一个问题，发言简洁
- 返回 JSON：{action, reply, reference}
"""
from .base import BaseAgent

# 三角色人设
ROLE_PROMPTS = {
    "technical": (
        "你是技术面试官，态度专业、严谨、有分寸。追问要落到具体技术细节："
        "原理、方案取舍、踩过的坑、数据指标。"
    ),
    "HR": (
        "你是 HR 面试官，态度亲和而专业。重点考察沟通表达、稳定性、价值观、"
        "职业规划、团队协作与抗压能力。"
    ),
    "stress": (
        "你是压力面试官，态度带有适度的质疑与施压，会主动挑战候选人回答中的漏洞，"
        "观察其抗压与应变能力，但不失专业。"
    ),
}

# 阶段中文名
STAGE_NAMES = {
    "opening": "开场自我介绍",
    "basic": "基础题",
    "deep": "深度题",
    "stress": "压力/场景题",
    "closing": "收尾反问",
}

_VALID_ACTIONS = {"next", "followup", "probe", "finish"}

_INTERVIEWER_SYSTEM_PROMPT = """你是一位经验丰富的面试官，正在主导一场真实面试。你通过对话评估候选人，并控制面试节奏。

行为准则：
1. 每次发言只问一个问题，语言简洁自然，符合人设（50~150 字）。
2. 根据候选人回答质量决策下一步：
   - 回答完整、切题、有深度 → action=next：先简短肯定，再自然地问出下一道题。
   - 回答过短（不足 30 字）或含糊空泛 → action=probe：请对方展开、举例说明。
   - 回答有深挖价值但不够透 → action=followup：顺着回答追问一个更深入的问题。
   - 回答跑题或过长 → 礼貌打断，把话题拉回本题（action 按上述三种其一，reply 先打断再引导）。
   - 这是最后一道题且回答已充分 → action=finish：给出整体收尾与结束语。
3. 不评判、不泄露评分，始终保持面试官口吻。

只输出 JSON，不要任何额外文字。JSON 结构：
{"action": "next|followup|probe|finish", "reply": "你的完整发言", "reference": "本回合参考要点（讲解/提示，供面试后复盘展示，控制在 50 字以内）"}"""


class InterviewerAgent(BaseAgent):
    """面试官 Agent。"""

    system_prompt = _INTERVIEWER_SYSTEM_PROMPT
    # 短回复场景：发言 50~150 字 + 参考要点 50 字，1024 绰绰有余，防止长篇输出拖慢对话
    MAX_OUTPUT_TOKENS = 1024

    def decide(
        self,
        *,
        role: str,
        stage_label: str,
        current_question: str,
        current_reference: str,
        next_question: str | None,
        conversation: list[dict],
        candidate_answer: str,
        resume_summary: str = "",
    ) -> dict:
        """根据候选人最新回答，决定面试官的下一步发言。

        返回 dict：{"action", "reply", "reference"}
        """
        persona = ROLE_PROMPTS.get(role, ROLE_PROMPTS["technical"])
        conv_text = _format_conversation(conversation)
        next_part = next_question or "（无，这是最后一道题）"
        resume_part = f"【候选人画像】{resume_summary}\n" if resume_summary else ""

        prompt = (
            f"{persona}\n"
            f"【当前阶段】{stage_label}\n"
            f"【候选人刚回答的问题】{current_question}\n"
            f"【该题参考要点】{current_reference or '无'}\n"
            f"{resume_part}"
            f"【候选人的最新回答】\n{candidate_answer}\n"
            f"【本轮对话（最近若干轮）】\n{conv_text}\n"
            f"【下一道题】{next_part}\n"
            "\n请按判定规则输出 JSON。"
        )

        result = self.chat_json(prompt, temperature=0.7)
        return self._validate(result)

    @staticmethod
    def _validate(result: dict) -> dict:
        action = str(result.get("action", "")).strip()
        if action not in _VALID_ACTIONS:
            # 兜底：非法动作视为 finish，避免流水线卡死
            action = "finish"
        return {
            "action": action,
            "reply": str(result.get("reply", "")).strip(),
            "reference": str(result.get("reference", "")).strip(),
        }


def _format_conversation(conversation: list[dict], *, tail: int = 8) -> str:
    """把最近若干轮消息格式化成可读文本。"""
    if not conversation:
        return "（无）"
    lines = []
    for msg in conversation[-tail:]:
        role = msg.get("role")
        label = "面试官" if role == "assistant" else "候选人"
        lines.append(f"{label}：{msg.get('content', '')}")
    return "\n".join(lines)
