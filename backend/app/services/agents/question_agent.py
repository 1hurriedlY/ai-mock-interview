"""面试题生成 Agent：按「面试官角色 × 目标岗位 × 简历分析结果」生成结构化题卡。

题卡五阶段（对应 config.STAGES）：
- opening: 开场自我介绍引导
- basic:   基础题（2-3 个）
- deep:    深度题（2-3 个，结合简历项目追问）
- stress:  压力/场景题（1-2 个）
- closing: 收尾反问（1-2 个，给候选人提问机会）

输出 JSON：
{
  "stages": {
    "opening": {"question": "请先做个自我介绍", "reference": "自我介绍要点"},
    "basic":  [{"question": "...", "reference": "参考要点"}, ...],
    "deep":   [{"question": "...", "reference": "参考要点"}, ...],
    "stress": [{"question": "...", "reference": "参考要点"}, ...],
    "closing":[{"question": "...", "reference": "参考要点"}, ...]
  }
}
"""
from ...config import STAGES
from .base import BaseAgent

_QUESTION_SYSTEM_PROMPT = """你是资深面试官与命题专家。请根据【目标岗位】、【面试官角色】、【候选人简历画像】生成一套结构化面试题卡。

题卡分 5 个阶段，每道题附"参考要点"（这道题考察什么、期望候选人在哪几个点作答）：

1. opening 开场：引导候选人做自我介绍（1 道）
2. basic 基础题：考察岗位核心基础技能（2-3 道）
3. deep 深度题：结合候选人简历中的项目，深入追问技术细节/设计取舍（2-3 道）
4. stress 压力/场景题：考察应变能力、冲突处理、极端场景（1-2 道）
5. closing 收尾：给候选人提问环节，问一个面试官会主动抛出的收尾问题（1 道）

【面试官角色】决定出题侧重：
- technical：深挖技术原理、架构、踩坑
- HR：考察沟通、稳定性、价值观、职业规划
- stress：偏压力施压、质疑简历、极限假设

只输出 JSON，不要任何额外文字。JSON 结构：
{
  "stages": {
    "opening": {"question": "…", "reference": "…"},
    "basic":  [{"question": "…", "reference": "…"}],
    "deep":   [{"question": "…", "reference": "…"}],
    "stress": [{"question": "…", "reference": "…"}],
    "closing": [{"question": "…", "reference": "…"}]
  }
}
要求：题目要具体、贴合岗位与简历，不要泛泛而谈；全部中文。"""

# 角色中文名映射（前端展示用）
ROLE_NAMES = {
    "technical": "技术面",
    "HR": "HR 行为面",
    "stress": "压力面",
}


class QuestionAgent(BaseAgent):
    """面试题生成 Agent。"""

    system_prompt = _QUESTION_SYSTEM_PROMPT

    def generate_card(
        self,
        *,
        job_title: str,
        role: str = "technical",
        resume_analysis: dict | None = None,
    ) -> dict:
        """生成题卡。

        resume_analysis 为简历分析 Agent 的输出（可为 None，无简历时按岗位通用出题）。
        """
        resume_part = ""
        if resume_analysis:
            resume_part = (
                "【候选人简历画像】\n"
                f"技能栈：{', '.join(resume_analysis.get('skills') or [])}\n"
                f"项目经历：{_format_projects(resume_analysis.get('projects') or [])}\n"
                f"亮点：{'; '.join(resume_analysis.get('highlights') or [])}\n"
                f"教育：{resume_analysis.get('education') or '未提供'}\n"
            )

        role_part = f"【面试官角色】{ROLE_NAMES.get(role, role)}"

        prompt = (
            f"【目标岗位】{job_title}\n"
            f"{role_part}\n"
            f"{resume_part}"
            "\n请生成这套面试的完整题卡。"
        )
        card = self.chat_json(prompt, temperature=0.7)
        # 规范化：确保五阶段键都存在（缺的补空）
        return self._normalize(card)

    @staticmethod
    def _normalize(card: dict) -> dict:
        stages = card.get("stages") or {}
        for stage in STAGES:
            if stage not in stages:
                stages[stage] = [] if stage != "opening" else {
                    "question": "请先做个自我介绍", "reference": ""
                }
        # opening 允许是 dict 或 list，统一为 list 便于流水线处理
        opening = stages["opening"]
        if isinstance(opening, dict):
            stages["opening"] = [opening]
        elif not isinstance(opening, list):
            stages["opening"] = [{"question": str(opening), "reference": ""}]
        # 其余阶段统一为 list
        for stage in ("basic", "deep", "stress", "closing"):
            val = stages[stage]
            if isinstance(val, dict):
                stages[stage] = [val]
            elif not isinstance(val, list):
                stages[stage] = []
        return {"stages": stages}


def _format_projects(projects: list) -> str:
    if not projects:
        return "无"
    lines = []
    for p in projects:
        lines.append(f"- {p.get('name')}：{p.get('description')}")
    return "\n".join(lines)
