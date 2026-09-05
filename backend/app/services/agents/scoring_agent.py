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
3. match_analysis 给出匹配度等级（高/中/低）与理由；其中 strengths 是候选人整场面试做得好的「优点」，gaps 是「不足/薄弱点」，各 2-4 条，均须结合具体回答实例（可引用对话原话），报告会以「面试优点与不足」单独展示
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

    # 逐题参考答案的生成独立成一次调用：与主评分解耦，失败不影响报告主体。
    _QA_PROMPT = """你在模拟一场真实的模拟面试复盘。下面会给你几道「面试官问题 + 候选人当时的回答」。

请对每一题，只写一段「候选人现在可以照着说出口的完整回答」，语气要像真人聊天那样自然：
- 开头可以用类似："我当时主要做了……""这个问题我是这么拆的：""说起来印象最深的是……"这类口语开场，正文第一人称
- 内容具体：有清晰脉络和真实感细节（数字、方案名、取舍理由、踩过的坑、怎么验证）
- 如果候选人当时的回答有漏洞或没说透，范例回答要把那部分补完整、示范更好的答法
- 绝对禁止：评价候选人（如"暴露不足""缺乏""未作答导致……"）、给建议、写考察点、写评分，只允许写"作答内容本身"

示例（参考风格，不要照抄内容）：
「这块我当时是这么处理的。系统改造前，每次对账要跑两个多小时，我先用日志把耗时分布拉出来，发现大头在对账单和流水表的 N+1 查询上。后来我把它改成按商户 ID 分批 + 双游标对齐，再配合幂等表去重，跑批就压到了 15 分钟左右；另外还加了失败重试和人工补偿入口，保证对不上账时有地方兜底。」

规则：
1. 只输出 JSON。强烈推荐数组：
   [{"index": 题目序号, "model_answer": "完整作答",
     "good_points": ["答得好的具体点"], "weak_points": ["欠缺/答得不好的具体点"]}]，
   序号从 1 开始、连续编号
2. model_answer 用中文、口语自然、可直接照着说，篇幅 120~250 字
3. 题目有几道就输出几条，不要合并、不要漏题
4. 某题候选人没回答时，同样给出该题该怎么答的完整范例
5. 每题附简短点评（只针对这题作答本身，不写套话）：
   good_points 1-2 条，指出答得好的具体点（可引用原话，如"用数字说明成果"）；
   weak_points 1-2 条，指出答得不好/漏掉的关键点；未作答则该题 weak_points 写「本题未作答」"""

    def generate_model_answers(
        self,
        qa_pairs: list[dict],
        *,
        job_title: str,
        role: str,
    ) -> list[dict]:
        """对逐题记录生成 AI 参考答案。

        qa_pairs: [{"question": ..., "answer": ...}, ...]
        返回: [{"question", "answer", "model_answer"}, ...]（与输入一一对应）。

        长对话会拆成小批（每批最多 4 题）调用，降低超长输出漏题/截断的概率。
        """
        if not qa_pairs:
            return []
        n = len(qa_pairs)
        CHUNK = 4
        answers: list[str] = [""] * n
        goods: list[list[str]] = [[] for _ in range(n)]
        weaks: list[list[str]] = [[] for _ in range(n)]

        logger = __import__("logging").getLogger(__name__)
        for start in range(0, n, CHUNK):
            sub = qa_pairs[start:start + CHUNK]
            lines = []
            for i, qa in enumerate(sub, start=1):
                answer = str(qa.get("answer") or "").strip()
                lines.append(
                    f"第 {i} 题\n问题：{str(qa.get('question') or '')[:900]}\n"
                    f"候选人当时的回答：{answer[:900] if answer else '（未回答）'}"
                )
            user_message = (
                f"【目标岗位】{job_title}\n【面试官角色】{role}\n\n"
                + "\n\n".join(lines)
                + "\n\n请输出这一批每一题的范例回答 JSON。"
            )
            try:
                result = self.chat_json(
                    user_message, system=self._QA_PROMPT, temperature=0.35
                )
            except Exception:
                logger.exception("逐题参考答案批次生成失败（第 %d 批），该批回退为空", start // CHUNK + 1)
                continue
            merged = self._normalize_qa(result, sub)
            for offset, item in enumerate(merged):
                idx = start + offset
                if idx >= n or not str(item.get("model_answer") or "").strip():
                    continue
                answers[idx] = item["model_answer"]
                goods[idx] = list(item.get("good_points") or [])
                weaks[idx] = list(item.get("weak_points") or [])

        return [
            {
                "question": str(qa.get("question") or ""),
                "answer": str(qa.get("answer") or ""),
                "model_answer": answers[i],
                "good_points": goods[i],
                "weak_points": weaks[i],
            }
            for i, qa in enumerate(qa_pairs)
        ]

    @classmethod
    def _normalize_qa(cls, result, qa_pairs: list[dict]) -> list[dict]:
        """把模型输出的逐题参考答案规范化并按题目顺序对齐。

        兼容常见返回形态：
        - 数组 [{"index":1,"model_answer":"…"}]（或带序号键的字典元素、纯文本串）
        - 包一层：{"answers/qna/items/data": [...]}
        - 数字键对象 {"1": "…"}
        - 嵌套对象 {"question_1": {"reference_answer": "…"}, ...} / {"q1": "…"}
        """
        import re

        def _text_of(value) -> str:
            """从字符串或含答案字段的对象里取出文本。"""
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, dict):
                for key in (
                    "model_answer", "reference_answer", "参考答案", "answer",
                    "reference", "content", "text",
                ):
                    val = value.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            return ""

        def _idx_of_key(key: str) -> int | None:
            m = re.search(r"(\d+)\s*$", str(key))
            return int(m.group(1)) if m else None

        raw = result if isinstance(result, list) else None
        if raw is None and isinstance(result, dict):
            for key in ("answers", "qna", "items", "data", "list"):
                if isinstance(result.get(key), list):
                    raw = result[key]
                    break

        if raw is None and isinstance(result, dict):
            # 数字键 / question_N / qN 等对象形态
            mapping: dict[int, str] = {}
            sequential: list[str] = []
            for k, v in result.items():
                text = _text_of(v)
                if not text:
                    continue
                idx = _idx_of_key(k)
                if idx is not None:
                    mapping.setdefault(idx, text)
                else:
                    sequential.append(text)
            if mapping:
                next_idx = (max(mapping) + 1) if mapping else 1
                for text in sequential:
                    mapping.setdefault(next_idx, text)
                    next_idx += 1
                raw = [{"index": i, "model_answer": mapping[i]} for i in sorted(mapping)]
            elif sequential:
                raw = [{"index": i, "model_answer": t} for i, t in enumerate(sequential, start=1)]
            else:
                raw = []
        if not isinstance(raw, list):
            raw = []

        def _crit_list(value, keys):
            """从 dict 字段/字符串中取出点评条目列表。"""
            if isinstance(value, str):
                return [value.strip()] if value.strip() else []
            if isinstance(value, list):
                return [str(x).strip() for x in value if str(x).strip()]
            if isinstance(value, dict):
                for k in keys:
                    if k in value:
                        return _crit_list(value[k], ())
            return []

        answers: dict[int, str] = {}
        goods: dict[int, list[str]] = {}
        weaks: dict[int, list[str]] = {}
        plain_texts: list[str] = []
        for item in raw:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    plain_texts.append(text)
                continue
            if not isinstance(item, dict):
                continue
            text = _text_of(item)
            idx = None
            for key in ("index", "idx", "id", "no", "序号", "题号"):
                val = item.get(key)
                if isinstance(val, (int, str)):
                    try:
                        idx = int(val)
                    except (TypeError, ValueError):
                        idx = None
                    if idx is not None:
                        break
            good = _crit_list(
                item.get("good_points", item), ("good_points", "goodPoints", "good", "优点", "答得好")
            )
            weak = _crit_list(
                item.get("weak_points", item), ("weak_points", "weakPoints", "weak", "不足", "欠缺", "答得不好")
            )
            if text:
                if idx is not None:
                    answers.setdefault(idx, text)
                    if good:
                        goods.setdefault(idx, []).extend(good)
                    if weak:
                        weaks.setdefault(idx, []).extend(weak)
                else:
                    plain_texts.append(text)

        # 纯文本/无序号文本：按出现顺序兜底对齐
        for i, text in enumerate(plain_texts, start=1):
            answers.setdefault(i, text)

        out = []
        for i, qa in enumerate(qa_pairs, start=1):
            out.append(
                {
                    "question": str(qa.get("question") or ""),
                    "answer": str(qa.get("answer") or ""),
                    "model_answer": answers.get(i, ""),
                    "good_points": goods.get(i, []),
                    "weak_points": weaks.get(i, []),
                }
            )
        return out

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
