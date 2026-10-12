"""报告服务：调用评分 Agent 生成报告并落库。

职责：
- 组装评分 Agent 需要的上下文（角色/岗位/简历/对话/表情序列）
- 调用 ScoringAgent.generate_report
- 把报告 JSON 落库 interview_reports
- 失败时提供兜底报告（AI 不可用时也不让流程崩溃）

ai_config：当前用户的模型配置（来自 ai_config_service.resolve_config），
为 None 时评分 Agent 回退 .env 里的全局默认。
"""
import json
import logging

from sqlalchemy.orm import Session

from .agents.scoring_agent import ScoringAgent
from ..models import InterviewReport

logger = logging.getLogger(__name__)


def generate_and_store_report(
    db: Session,
    *,
    session_id: int,
    role: str,
    job_title: str,
    resume_text: str = "",
    resume_summary: str = "",
    conversation: list[dict],
    expression_seq: list[dict] | None = None,
    ai_config: dict | None = None,
) -> InterviewReport:
    """生成评分报告并落库，返回 ORM 对象。

    conversation 为完整对话记录（user/assistant 交替）。
    expression_seq 为可选表情时间轴（视觉模块）。
    ai_config 为可选模型配置（用户自定义模型）。
    """
    # 已有报告则直接返回（幂等，防止重复调用大模型）
    existing = db.query(InterviewReport).filter(
        InterviewReport.session_id == session_id
    ).first()
    if existing:
        return existing

    try:
        report_data = ScoringAgent(ai_config).generate_report(
            role=role,
            job_title=job_title,
            resume_text=resume_text,
            resume_summary=resume_summary,
            conversation=conversation,
            expression_seq=expression_seq,
        )
    except Exception as exc:
        logger.exception("评分 Agent 调用失败，使用兜底报告")
        report_data = _fallback_report(exc)

    # 逐题复盘：AI 重新生成每道题的参考答案（独立调用，失败回退空 → 前端用面试时参考要点兜底）
    qa_pairs = _build_qa_pairs(conversation)
    if qa_pairs:
        qa_agent = ScoringAgent(ai_config)
        qa_agent.MAX_OUTPUT_TOKENS = 8192  # 逐题长答案，放宽输出上限防长对话截断
        qna = qa_agent.generate_model_answers(
            qa_pairs, job_title=job_title, role=role
        )
        # 去掉没有生成出参考答案的题目（宁缺勿错，避免空内容入库）
        report_data["qna"] = [
            item for item in qna
            if str(item.get("model_answer") or "").strip()
        ]
    else:
        report_data["qna"] = []

    report = InterviewReport(
        session_id=session_id,
        summary=report_data.get("summary") or "",
        overall_score=int(report_data.get("overall_score") or 0),
        dimensions=json.dumps(report_data.get("dimensions") or {}, ensure_ascii=False),
        match_analysis=json.dumps(report_data.get("match_analysis") or {}, ensure_ascii=False),
        suggestions=json.dumps(report_data.get("suggestions") or [], ensure_ascii=False),
        expression_analysis=json.dumps(
            report_data.get("expression_analysis") or {}, ensure_ascii=False
        ),
        qna=json.dumps(report_data.get("qna") or [], ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _fallback_report(exc: Exception) -> dict:
    """AI 调用失败时的兜底报告，分数中性、给出提示。"""
    return {
        "summary": f"本次面试评分报告生成失败（{exc}），请检查大模型服务后重试。",
        "overall_score": 0,
        "dimensions": {"专业技能": 0, "沟通表达": 0, "逻辑思维": 0, "项目经验": 0, "岗位匹配": 0},
        "match_analysis": {
            "match_level": "未知",
            "reason": "评分服务不可用",
            "strengths": [],
            "gaps": [],
        },
        "suggestions": ["请确认模型配置正确（设置页自定义模型或 .env 默认）后重新生成报告。"],
        "expression_analysis": {},
        "qna": [],
    }


def _build_qa_pairs(conversation: list[dict]) -> list[dict]:
    """把线性对话整理成逐题结构：面试官问题 + 其后紧邻的候选人回答。

    每一条 assistant 消息视为一题（开场/追问都算）；紧随其后的连续 user 消息
    合并为该题的候选人回答。
    """
    pairs = []
    for i, msg in enumerate(conversation):
        if msg.get("role") != "assistant":
            continue
        question = str(msg.get("content") or "").strip()
        if not question:
            continue
        answer_parts = []
        for nxt in conversation[i + 1:]:
            if nxt.get("role") == "user":
                answer_parts.append(str(nxt.get("content") or ""))
            else:
                break
        pairs.append({"question": question, "answer": "\n".join(answer_parts)})
    return pairs
