"""简历分析 Agent：从简历文本抽取结构化信息（技能栈/项目经历/亮点/教育）。

输出 JSON 结构（供后续题卡生成与面试官使用）：
{
  "summary": "一句话概况",
  "skills": ["Python", "FastAPI", ...],
  "projects": [{
    "name": "...",
    "description": "一句话说明",
    "my_role": "我在其中的职责/贡献",
    "tech_stack": ["..."],
    "result": "一段量化成果或业务结果（无数据则写实现价值）"
  }],
  "highlights": ["...", "..."],
  "education": "本科 · 计算机科学"
}
"""
from .base import BaseAgent

_RESUME_SYSTEM_PROMPT = """你是资深技术面试官与 HR，擅长从简历中提炼候选人画像。
请阅读简历原文，抽取结构化信息，只输出 JSON 对象，不要输出任何额外文字。

JSON 字段：
- summary: string，一句话概括候选人定位
- skills: string 数组，技术栈/技能（按熟练度排序，前 10 个）
- projects: 数组，每项结构：
  { name: string 项目名,
    description: string 一句话说明项目是什么，
    my_role: string 我的职责/个人贡献（做了什么、负责哪块），
    tech_stack: string 数组，用到的关键技术，
    result: string 量化成果或业务结果（性能/规模/收益数字；简历没给数字就写实现价值） }
- highlights: string 数组，工作亮点/成绩（如性能提升、获奖，最多 5 条）
- education: string，教育背景一句话（无则空字符串）

要求：
1. 只依据简历原文，不要编造。
2. 简历未提到的字段给空数组或空字符串；描述要具体，别把"负责开发"这类空话当职责。
3. 所有值用中文（专有名词可保留英文）。"""


class ResumeAgent(BaseAgent):
    """简历分析 Agent。"""

    system_prompt = _RESUME_SYSTEM_PROMPT

    def analyze(self, resume_text: str) -> dict:
        """分析简历文本，返回结构化 JSON。"""
        prompt = f"请分析以下简历文本：\n\n{resume_text}"
        return self.chat_json(prompt, temperature=0.2)
