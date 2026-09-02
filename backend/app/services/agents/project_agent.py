"""项目渠道 / 讲项目话术 Agent。

两个能力：
1. generate_channels()：求职/接单渠道平台清单（全职招聘、外包接单、开源攒项目，
   按免费/付费/适合新人分类），帮求职者快速找到去哪里找机会。
2. generate_script()：用 STAR 法把候选人做过的项目拆成可背诵的面试话术
   （背景-任务-行动-结果 + 踩坑复盘 + 深挖追问应对）。

输出 JSON 结构：
channels:
{
  "summary": "一句话总览",
  "categories": [
    {"category": "全职招聘/外包接单/开源攒项目",
     "items": [{"name": "平台名", "free": bool, "suitable": "适合人群", "description": "用法建议"}]}
  ]
}

script:
{
  "project_name": "项目名",
  "summary": "30 秒电梯介绍",
  "star": {"situation": 背景, "task": 任务, "action": 行动, "result": 结果},
  "deep_dive": [{"question": 追问, "answer": 应对}],
  "pitfalls": [{"issue": 踩坑, "lesson": 复盘}],
  "script": "完整 3 分钟讲项目话术"
}
"""
from .base import BaseAgent

_PROJECT_CHANNELS_PROMPT = """你是求职与接单渠道专家。请给出一份求职/接单渠道平台清单，覆盖三类：全职招聘、外包接单、开源攒项目，帮求职者（尤其初级/转行）知道去哪里找机会、怎么用。

输出 JSON：
{
  "summary": "一句话总览",
  "categories": [
    {
      "category": "全职招聘 / 外包接单 / 开源攒项目",
      "items": [
        {
          "name": "平台名",
          "free": true/false,
          "suitable": "适合人群（应届/1-3年/接单/新人攒经验…）",
          "description": "一句话说明怎么用、注意什么"
        }
      ]
    }
  ]
}

要求：
1. 每类至少 3 个真实平台（含国内与国际：BOSS直聘、拉勾、Freelancer、Upwork、GitHub、码云等），不要编造不存在的平台
2. free 标记是否免费可用：true 免费，false 有付费/会员门槛
3. 每个平台给具体使用建议（怎么找、怎么谈），不要泛泛而谈
只输出 JSON，不要任何额外文字。全部用中文（平台名可保留原名）。"""

_PROJECT_SCRIPT_PROMPT = """你是面试表达教练，擅长用 STAR 法把候选人做过的项目讲成面试官爱听的"讲项目脚本"。

请根据【项目名称】与【项目描述】（可为空）生成一份可背诵的讲项目话术。描述为空时，基于项目名给出 STAR 框架模板，标注【待补充】让候选人填实际数据。

输出 JSON：
{
  "project_name": "项目名",
  "summary": "30 秒电梯介绍（一句话说清项目是什么、你做了什么、结果如何）",
  "star": {
    "situation": "背景（为什么要做这个项目）",
    "task": "任务（你的职责与目标）",
    "action": "行动（具体怎么做的：技术选型/方案/关键决策，突出你的贡献）",
    "result": "结果（量化成果，如性能提升 xx%、上线 xx 用户）"
  },
  "deep_dive": [{"question": "面试官可能追问的问题", "answer": "应对话术"}],
  "pitfalls": [{"issue": "踩过的一个坑", "lesson": "复盘出的经验"}],
  "script": "完整讲项目话术（3 分钟版，可直接背）"
}

要求：
1. action 是重点，要具体到技术方案与个人贡献，避免"我们用了 xxx"的模糊表述
2. result 尽量量化；没有数据用"提升了/解决了/上线了"等可验证描述
3. script 是完整可背的口语化文本，第一人称，约 3 分钟
4. 描述为空时在相关字段标注【待补充】
只输出 JSON，不要任何额外文字。全部用中文。"""


class ProjectAgent(BaseAgent):
    """求职渠道清单 / 讲项目话术 Agent。"""

    def generate_channels(self) -> dict:
        """生成求职/接单渠道平台清单。"""
        result = self.chat_json("请生成一份求职/接单渠道平台清单。", system=_PROJECT_CHANNELS_PROMPT)
        return self._normalize_channels(result)

    def generate_script(self, project_name: str, description: str = "") -> dict:
        """用 STAR 法生成讲项目面试话术。"""
        desc_part = f"【项目描述】{description}" if description else "【项目描述】（未提供，请给 STAR 模板）"
        prompt = (
            f"【项目名称】{project_name}\n"
            f"{desc_part}\n"
            "请生成这份项目的讲项目面试话术。"
        )
        result = self.chat_json(prompt, system=_PROJECT_SCRIPT_PROMPT, temperature=0.5)
        return self._normalize_script(result, project_name)

    # ---------- 兜底规范化 ----------
    @staticmethod
    def _normalize_channels(result: dict) -> dict:
        """渠道清单兜底：保证 categories/items 结构完整。"""
        summary = str(result.get("summary") or "")

        categories = result.get("categories") or []
        if isinstance(categories, dict):
            categories = [categories]
        if not isinstance(categories, list):
            categories = []

        out = []
        for cat in categories:
            if not isinstance(cat, dict):
                continue
            items = []
            raw_items = cat.get("items") or []
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
            for it in raw_items if isinstance(raw_items, list) else []:
                if isinstance(it, dict):
                    items.append(
                        {
                            "name": str(it.get("name") or ""),
                            "free": bool(it.get("free")),
                            "suitable": str(it.get("suitable") or ""),
                            "description": str(it.get("description") or ""),
                        }
                    )
            out.append({"category": str(cat.get("category") or "其他"), "items": items})

        return {"summary": summary, "categories": out}

    @staticmethod
    def _normalize_script(result: dict, project_name: str) -> dict:
        """讲项目话术兜底：保证 STAR/追问/踩坑/完整脚本齐全。"""
        star = result.get("star") or {}
        if not isinstance(star, dict):
            star = {}
        norm_star = {k: str(star.get(k) or "") for k in ("situation", "task", "action", "result")}

        deep_dive = []
        for d in (result.get("deep_dive") or []):
            if isinstance(d, dict):
                deep_dive.append(
                    {"question": str(d.get("question") or ""), "answer": str(d.get("answer") or "")}
                )

        pitfalls = []
        for p in (result.get("pitfalls") or []):
            if isinstance(p, dict):
                pitfalls.append(
                    {"issue": str(p.get("issue") or ""), "lesson": str(p.get("lesson") or "")}
                )

        script = str(result.get("script") or "").strip()
        if not script:
            script = f"（{project_name} 的完整话术未生成，请重新生成。）"

        return {
            "project_name": str(result.get("project_name") or project_name),
            "summary": str(result.get("summary") or ""),
            "star": norm_star,
            "deep_dive": deep_dive,
            "pitfalls": pitfalls,
            "script": script,
        }
