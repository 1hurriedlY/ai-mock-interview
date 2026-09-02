"""历史路由：面试会话列表与详情回看。

- GET /api/history           当前用户所有会话（按时间倒序），带报告概要
- GET /api/history/{id}      单个会话详情：完整消息（含参考要点）+ 报告 + 元信息
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config
from ..auth import get_current_user
from ..database import get_db
from ..models import ChatMessage, InterviewReport, InterviewSession, User
from ..redis_client import redis_client
from ..services.agents.question_agent import ROLE_NAMES

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- 响应模型 ----------
class SessionSummary(BaseModel):
    """会话列表项：概要信息，不含消息明细。"""

    id: int
    job_title: str
    interviewer_role: str
    interviewer_name: str
    status: str
    created_at: str
    ended_at: Optional[str] = None
    message_count: int
    report: Optional[dict] = None  # 报告概要 {overall_score, summary 前 80 字}


class MessageItem(BaseModel):
    """一条聊天消息（详情回看用）。"""

    id: int
    role: str
    content: str
    reference: Optional[str] = None
    created_at: str


class SessionDetail(BaseModel):
    """单个会话完整详情。"""

    id: int
    job_title: str
    interviewer_role: str
    interviewer_name: str
    status: str
    created_at: str
    ended_at: Optional[str] = None
    resume_text: Optional[str] = None
    messages: list[MessageItem]
    report: Optional[dict] = None
    stage: Optional[str] = None  # 当前题卡阶段（未结束时供前端恢复现场）


@router.delete("/{session_id}")
def delete_history(
    session_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除一条历史会话：级联删除消息与报告，并清理 Redis 缓存。"""
    session = _get_session_or_404(db, session_id)
    if session.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权删除该会话")

    # 先删从表（消息、报告），再删会话本身
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.query(InterviewReport).filter(InterviewReport.session_id == session_id).delete()
    db.delete(session)
    db.commit()

    # Redis 侧的会话上下文/题卡/阶段缓存一并清理（try 内部自行降级）
    redis_client.delete_session(session_id)

    logger.info("用户 %s 删除历史会话 %s", current.id, session_id)
    return {"ok": True, "session_id": session_id}


# ---------- 内部工具 ----------
def _fmt(dt) -> str:
    """时间格式化为字符串，None 返回 None。"""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _role_name(role: str) -> str:
    """角色 key → 中文名（未知名回退原值）。"""
    return ROLE_NAMES.get(role, role)


def _report_summary(report: InterviewReport | None) -> dict | None:
    """报告概要点：总分 + 评语摘要（列表页足够）。"""
    if report is None:
        return None
    summary = (report.summary or "")[:80]
    return {
        "id": report.id,
        "overall_score": report.overall_score,
        "summary": summary,
    }


def _report_full(report: InterviewReport | None) -> dict | None:
    """报告完整 JSON（详情页）。"""
    if report is None:
        return None

    def _load(raw: str | None, default):
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    return {
        "id": report.id,
        "summary": report.summary or "",
        "overall_score": report.overall_score,
        "dimensions": _load(report.dimensions, []),
        "match_analysis": _load(report.match_analysis, {}),
        "suggestions": _load(report.suggestions, []),
        "expression_analysis": _load(report.expression_analysis, {}),
        "created_at": _fmt(report.created_at),
    }


def _get_session_or_404(db: Session, session_id: int) -> InterviewSession:
    """按 id 查询会话，不存在返回 404。"""
    s = db.get(InterviewSession, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return s


# ---------- 路由 ----------
@router.get("", response_model=list[SessionSummary])
def list_history(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户的会话列表（时间倒序），带报告概要。"""
    sessions = db.scalars(
        select(InterviewSession)
        .where(InterviewSession.user_id == current.id)
        .order_by(InterviewSession.created_at.desc(), InterviewSession.id.desc())
    ).all()

    # 一次查出各会话的消息数，避免 N+1 查询
    message_counts = dict(
        db.execute(
            select(ChatMessage.session_id, func.count(ChatMessage.id)).group_by(
                ChatMessage.session_id
            )
        ).all()
    )
    # 一次查出各会话的报告
    reports = {
        r.session_id: r
        for r in db.scalars(
            select(InterviewReport).where(
                InterviewReport.session_id.in_([s.id for s in sessions])
            )
        ).all()
    } if sessions else {}

    return [
        SessionSummary(
            id=s.id,
            job_title=s.job_title,
            interviewer_role=s.interviewer_role,
            interviewer_name=_role_name(s.interviewer_role),
            status=s.status,
            created_at=_fmt(s.created_at),
            ended_at=_fmt(s.ended_at),
            message_count=message_counts.get(s.id, 0),
            report=_report_summary(reports.get(s.id)),
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionDetail)
def get_history_detail(
    session_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """单个会话详情：完整消息（含 reference）+ 报告 JSON。"""
    session = _get_session_or_404(db, session_id)
    if session.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")

    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
    ).all()

    report = db.scalar(
        select(InterviewReport).where(InterviewReport.session_id == session_id)
    )

    # 当前题卡阶段（未结束时有卡时返回 stage；Redis 不可用则 None，前端不强制）
    stage: Optional[str] = None
    if session.status != "completed":
        card = redis_client.get_question_card(session_id)
        if card:
            state = (card.get("_state") or {})
            idx = state.get("stage_idx", 0)
            stage = config.STAGES[idx] if idx < len(config.STAGES) else None

    return SessionDetail(
        id=session.id,
        job_title=session.job_title,
        interviewer_role=session.interviewer_role,
        interviewer_name=_role_name(session.interviewer_role),
        status=session.status,
        created_at=_fmt(session.created_at),
        ended_at=_fmt(session.ended_at),
        resume_text=session.resume_text,
        messages=[
            MessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                reference=m.reference,
                created_at=_fmt(m.created_at),
            )
            for m in messages
        ],
        report=_report_full(report),
        stage=stage,
    )
