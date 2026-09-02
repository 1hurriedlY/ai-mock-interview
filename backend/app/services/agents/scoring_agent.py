"""评分 Agent：面试结束后，综合对话、简历与表情数据，输出多维评分报告。

输入：角色、岗位、简历文本/画像、完整对话、表情时间轴（可选）。
输出 JSON：
{
  "summary": 总体评语（2-3 句，中文）,
  "overall_score": 0-100 整数,
  "dimensions": {"专业技能": 0-100, "沟通表达": ..., "逻辑思维": ..., "项目经验": ..., "岗位匹配": ...},
  "match_analysis": {
    "match_level": "高/中/低"（与岗位匹配度）,
    "reason": 匹配理由,
    "strengths": [候选人亮点],
    "gaps": [不足/风险]
  },
  "suggestions": [具体可执行的改进建议, ...],
  "expression_analysis": {"comment": 表情点评, "highlights": [...]}   // 有表情数据时才生成
}
"""
from .base import BaseAgent

_SCORING_SYSTEM_PROMPT = """你是资深面试官与职业评估专家。请基于一场模拟面试的完整记录，输出一份客观、具体、可执行的评估报告。

评分维度（各 0-100，整数）：
- 专业技能：技术原理掌握深度、方案取舍合理性
- 沟通表达：表达清晰度、条理性、感染力
- 逻辑思维：回答结构、推理严谨性、举例说服力
- 项目经验：项目复杂度、个人角色、落地成果
- 岗位匹配：与目标岗位的契合程度

要求：
1. 评分要基于面试记录中的实际表现，不要空泛，避免一律给高分；明显不足要体现在分数里
2. summary 是 2-3 句总体评语，语气专业中肯
3. match_analysis 给出匹配度等级（高/中/低）与理由，strengths/gaps 各列出 2-4 条具体点
4. suggestions 给出 3-5 条可执行的改进建议（具体到"怎么做"）
5. 若提供了表情时间轴，结合表情数据点评候选人的情绪状态、应变与抗压表现（expression_analysis.comment）
6. 只输出 JSON，不要任何额外文字

必须严格使用以下键名，不得改用英文或其他键名：
- overall_score：0-100 整数
- dimensions：必须是对象，键固定为「专业技能」「沟通表达」「逻辑思维」「项目经验」「岗位匹配」，值 0-100 整数
- match_analysis.match_level：字符串，取「高」「中」「低」之一
- expression_analysis：仅在提供表情时间轴时输出，包含 comment 与 highlights"""


class ScoringAgent(BaseAgent):
    """多维评分 Agent。"""

    system_prompt = _SCORING_SYSTEM_PROMPT

    # 五维默认键（前端雷达图依赖）
    DIMENSION_KEYS = ["专业技能", "沟通表达", "逻辑思维", "项目经验", "岗位匹配"]
    # 模型偶发输出英文键，做别名映射（LLM 输出不稳兜底）
    _DIM_ALIASES = {
        "professional_skills": "专业技能",
        "communication": "沟通表达",
        "logical_thinking": "逻辑思维",
        "project_experience": "项目经验",
        "job_match": "岗位匹配",
        "matching_degree": "岗位匹配",
    }

    def generate_report(
        self,
        *,
        role: str,
        job_title: str,
        resume_text: str = "",
        resume_summary: str = "",
        conversation: list[dict],
        expression_seq: list[dict] | None = None,
    ) -> dict:
        """根据面试记录生成评分报告。

        conversation: [{"role": "user"/"assistant", "content": ...}, ...]
        expression_seq: [{"time": 秒, "expression": 表情, "confidence": 0-1}, ...]
        """
        expression_part = ""
        if expression_seq:
            expression_part = (
                "【表情时间轴】\n"
                + _format_expression(expression_seq)
                + "\n请结合表情数据分析候选人情绪与抗压表现。"
            )

        resume_part = ""
        if resume_text or resume_summary:
            resume_part = f"【候选人简历】\n{resume_summary or resume_text[:1500]}\n"

        conv_text = _format_conversation(conversation)

        prompt = (
            f"【目标岗位】{job_title}\n"
            f"【面试官角色】{role}\n"
            f"{resume_part}"
            f"【面试对话记录】\n{conv_text}\n"
            f"{expression_part}"
            "\n请输出评估报告 JSON。"
        )

        result = self.chat_json(prompt, temperature=0.4)
        return self._normalize(result, expression_seq)

    @classmethod
    def _normalize(cls, result: dict, expression_seq: list[dict] | None) -> dict:
        """兜底规范化：字段缺失/类型错误时给默认值，保证前端渲染不崩。"""
        dims = result.get("dimensions")
        if isinstance(dims, dict):
            # 中文键直接取；英文/别名键映射回中文键
            for alias, zh in cls._DIM_ALIASES.items():
                if alias in dims and zh not in dims:
                    dims[zh] = dims.pop(alias)
        elif isinstance(dims, list):
            dims = {k: v for k, v in zip(cls.DIMENSION_KEYS, dims)}
        else:
            # 模型偶发把五维直接平铺到 scores 键
            dims = result.get("scores") or {}
            if isinstance(dims, list):
                dims = {k: v for k, v in zip(cls.DIMENSION_KEYS, dims)}
            elif not isinstance(dims, dict):
                dims = {}
            for alias, zh in cls._DIM_ALIASES.items():
                if alias in dims and zh not in dims:
                    dims[zh] = dims.pop(alias)
        dims = {k: _clamp_score(dims.get(k)) for k in cls.DIMENSION_KEYS}

        match = result.get("match_analysis") or {}
        if not isinstance(match, dict):
            match = {}
        # 兼容英文键 level
        match_level = str(
            match.get("match_level")
            or match.get("level")
            or (result.get("match_level") or "中")
        )

        expr_ok = bool(expression_seq)
        expr_data = result.get("expression_analysis")
        if not isinstance(expr_data, dict):
            expr_data = {}

        # 表情时间轴：模型输出里的时间轴（timeline）不可靠，一律用原始输入序列
        # （前端采样点/历史报告都是 time+expression 结构），点评文字用模型输出。
        raw_seq = expression_seq or []
        timeline = []
        for item in raw_seq:
            exp = str(item.get("expression") or "neutral")
            if exp in ("no_face",):  # 无人脸断点不渲染
                continue
            t = _to_int(item.get("time"))
            if t is None:
                continue
            conf = float(item.get("confidence") or 0.8)
            timeline.append({"time": t, "expression": exp, "confidence": max(0.0, min(1.0, conf))})
        timeline.sort(key=lambda s: s["time"])  # 采样到达顺序可能乱，统一升序

        # overall_score 缺失/为 0 但五维有分时，用五维均值兜底
        overall = _clamp_score(result.get("overall_score"))
        if overall == 0 and any(dims.values()):
            overall = round(sum(dims.values()) / len(dims))

        # summary 缺失/为空时，用匹配度理由兜底（保证报告页有总评）
        summary = str(result.get("summary") or "").strip()
        if not summary:
            summary = str(match.get("reason") or "本次面试评分报告已生成。").strip()

        return {
            "summary": summary,
            "overall_score": overall,
            "dimensions": dims,
            "match_analysis": {
                "match_level": match_level,
                "reason": str(match.get("reason") or ""),
                "strengths": list(match.get("strengths") or result.get("strengths") or []),
                "gaps": list(match.get("gaps") or result.get("gaps") or []),
            },
            "suggestions": list(result.get("suggestions") or []),
            "expression_analysis": (
                {
                    "comment": str(expr_data.get("comment") or ""),
                    "highlights": list(expr_data.get("highlights") or []),
                    "timeline": timeline,
                }
                if expr_ok
                else {}
            ),
        }


def _clamp_score(value) -> int:
    """把任意分数值转成 0-100 整数；缺失/非法返回 0。"""
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, score))


def _to_int(value):
    """把 time 转 int；非法返回 None。"""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _format_conversation(conversation: list[dict], *, tail: int = 30) -> str:
    """把最近若干轮对话格式化成可读文本，防止超长截断。"""
    if not conversation:
        return "（无对话记录）"
    lines = []
    for msg in conversation[-tail:]:
        role = msg.get("role")
        label = "面试官" if role == "assistant" else "候选人"
        content = str(msg.get("content", ""))[:800]  # 每条截断，防超长
        lines.append(f"{label}：{content}")
    return "\n".join(lines)


def _format_expression(seq: list[dict]) -> str:
    """把表情时间轴压缩成文本摘要。"""
    if not seq:
        return "（无）"
    parts = []
    for item in seq[-60:]:  # 最多取最近 60 个采样点
        t = item.get("time", 0)
        exp = item.get("expression", "neutral")
        conf = float(item.get("confidence", 0.8))
        parts.append(f"{t}s:{exp}({conf:.2f})")
    return "、".join(parts)
