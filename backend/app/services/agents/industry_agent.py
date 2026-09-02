"""行业调研 Agent：把陌生行业结构化拆解成求职者能直接用的行业报告。

面向场景：候选人遇到完全陌生的行业 → 生成一份从 0 到 1 的行业认知报告，
包括产业链、头部玩家、商业模式、趋势、岗位技能与面试常见问题，可复用进面试准备。

输出 JSON 结构：
{
  "industry": "行业名",
  "overview": "一句话总体概览",
  "industry_chain": [{"name": "上游/中游/下游…", "description": "…"}],
  "key_players": [{"name": "企业名", "type": "头部/新锐/平台…", "description": "…"}],
  "business_models": [{"name": "模式名", "description": "…"}],
  "trends": ["趋势 1", "趋势 2", …],
  "job_skills": [{"skill": "技能名", "level": "必须/加分", "description": "…"}],
  "interview_questions": [{"question": "面试问题", "angle": "考察点"}]
}
"""
from .base import BaseAgent

_INDUSTRY_SYSTEM_PROMPT = """你是行业研究员与求职规划顾问，擅长把一个陌生行业讲清楚、讲人话，让求职者从完全陌生到能上场面试。

请针对【目标行业】输出一份结构化行业报告。要求：

1. 内容要具体、真实，不要空话套话；用当下（2026 年前后）的真实行业格局
2. overview：一句话说清这个行业是做什么的、有多大体量
3. industry_chain：产业链拆解（上游/中游/下游，3-6 个环节），每个环节说明做什么、代表玩家是谁
4. key_players：头部玩家 4-8 家（含国内外），每项给出 type（头部企业/新锐独角兽/平台/国家队等）与一句话简介
5. business_models：2-5 种主流商业模式（谁付费、怎么盈利）
6. trends：3-6 条行业趋势（技术/政策/市场方向，2026 年前后）
7. job_skills：对应岗位的核心技能清单 5-8 条，每项标明 level：必须/加分，并说明为什么需要
8. interview_questions：面试官常问的问题 4-6 个，每项给出 question 与 angle（面试官在考察什么）

只输出 JSON，不要任何额外文字。全部用中文（专有名词/英文缩写可保留）。JSON 键名严格使用：
industry、overview、industry_chain、key_players、business_models、trends、job_skills、interview_questions
各数组元素字段名严格使用：name/description、type、skill/level/description、question/angle。"""


class IndustryAgent(BaseAgent):
    """行业调研 Agent：陌生行业结构化拆解。"""

    system_prompt = _INDUSTRY_SYSTEM_PROMPT
    # 行业报告是最长的结构化输出（产业链/玩家/模式/趋势/技能/面试题），放宽到模型上限
    MAX_OUTPUT_TOKENS = 8192

    def research(self, industry_name: str) -> dict:
        """调研一个行业，返回结构化报告。"""
        prompt = f"【目标行业】{industry_name}\n请输出该行业的结构化调研报告 JSON。"
        result = self.chat_json(prompt, temperature=0.5)
        return self._normalize(result, industry_name)

    @staticmethod
    def _normalize(result: dict, industry_name: str) -> dict:
        """兜底规范化：字段缺失/类型错误给空默认值，保证前端渲染不崩。"""

        def _as_list(value) -> list:
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                return [value]
            if value in (None, ""):
                return []
            return [{"name": str(value), "description": ""}]

        def _as_dict_list(value) -> list:
            out = []
            for item in _as_list(value):
                if isinstance(item, dict):
                    out.append(item)
                else:
                    out.append({"name": str(item), "description": ""})
            return out

        overview = str(result.get("overview") or "")
        if not overview:
            overview = f"「{industry_name}」是当前一个值得关注的行业方向。"
        # 数组元素兜底补全键
        chain = [
            {**{"name": "", "description": ""}, **{k: (i.get(k) or "") for k in ("name", "description")}}
            for i in _as_dict_list(result.get("industry_chain"))
        ]
        players = [
            {
                "name": i.get("name") or "",
                "type": i.get("type") or "行业玩家",
                "description": i.get("description") or "",
            }
            for i in _as_dict_list(result.get("key_players"))
            if isinstance(i, dict)
        ]
        bm = [
            {"name": i.get("name") or "", "description": i.get("description") or ""}
            for i in _as_dict_list(result.get("business_models"))
        ]
        trends = [str(t) for t in (result.get("trends") or []) if str(t).strip()]
        job_skills = []
        for i in _as_dict_list(result.get("job_skills")):
            if isinstance(i, dict):
                job_skills.append({
                    "skill": i.get("skill") or i.get("name") or "",
                    "level": i.get("level") or "必须",
                    "description": i.get("description") or "",
                })
        questions = []
        for i in _as_dict_list(result.get("interview_questions")):
            if isinstance(i, dict):
                questions.append({
                    "question": i.get("question") or i.get("name") or "",
                    "angle": i.get("angle") or i.get("description") or "",
                })

        return {
            "industry": str(result.get("industry") or industry_name),
            "overview": overview,
            "industry_chain": chain,
            "key_players": players,
            "business_models": bm,
            "trends": trends,
            "job_skills": job_skills,
            "interview_questions": questions,
        }
