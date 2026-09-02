"""报告服务：调用评分 Agent 生成报告并落库。

职责：
- 组装评分 Agent 需要的上下文（角色/岗位/简历/对话/表情序列）
- 调用 ScoringAgent.generate_report
- 把报告 JSON 落库 interview_reports
- 失败时提供兜底报告（AI 不可用时也不让流程崩溃）
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
) -> InterviewReport:
    """生成评分报告并落库，返回 ORM 对象。

    conversation 为完整对话记录（user/assistant 交替）。
    expression_seq 为可选表情时间轴（视觉模块）。
    """
    # 已有报告则直接返回（幂等，防止重复调用大模型）
    existing = db.query(InterviewReport).filter(
        InterviewReport.session_id == session_id
    ).first()
    if existing:
        return existing

    try:
        report_data = ScoringAgent().generate_report(
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
        "suggestions": ["请确认 DASHSCOPE_API_KEY 配置正确后重新生成报告。"],
        "expression_analysis": {},
    }
