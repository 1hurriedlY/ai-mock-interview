"""管理员路由：查看与管理所有账号及其数据（仅 is_admin 可访问）。

- GET    /api/admin/users        所有用户列表（含各自数据量统计）
- DELETE /api/admin/users/{id}   删除某用户及其全部数据（管理员账号受保护）
- GET    /api/admin/sessions     所有用户的面试会话（含所属用户名）
- DELETE /api/admin/sessions/{id} 删除任意一场面试会话（级联消息/报告）
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import (
    ChatMessage,
    IndustryReport,
    InterviewReport,
    InterviewSession,
    ProjectReport,
    User,
)
from ..redis_client import redis_client
from ..services.agents.question_agent import ROLE_NAMES

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- 响应模型 ----------
class AdminUserItem(BaseModel):
    """用户列表项 + 数据量统计。"""

    id: int
    username: str
    is_admin: bool
    created_at: str
    session_count: int
    industry_count: int
    project_count: int


class AdminSessionItem(BaseModel):
    """全局面试会话列表项。"""

    id: int
    user_id: int
    username: str
    job_title: str
    interviewer_role: str
    interviewer_name: str
    status: str
    created_at: str
    ended_at: Optional[str] = None
    message_count: int
    has_report: bool


# ---------- 内部工具 ----------
def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def _user_counts(db: Session, user_id: int) -> dict:
    """某个用户各业务表的数据量（会话/行业报告/求职报告）。"""
    return {
        "session_count": db.scalar(
            select(func.count(InterviewSession.id)).where(
                InterviewSession.user_id == user_id
            )
        )
        or 0,
        "industry_count": db.scalar(
            select(func.count(IndustryReport.id)).where(IndustryReport.user_id == user_id)
        )
        or 0,
        "project_count": db.scalar(
            select(func.count(ProjectReport.id)).where(ProjectReport.user_id == user_id)
        )
        or 0,
    }


# ---------- 路由 ----------
@router.get("/users", response_model=list[AdminUserItem])
def list_users(
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """所有用户及其数据量（便于管理员掌握全局使用情况）。"""
    users = db.scalars(
        select(User).order_by(User.id.asc())
    ).all()
    return [
        AdminUserItem(
            id=u.id,
            username=u.username,
            is_admin=u.is_admin,
            created_at=_fmt(u.created_at),
            **_user_counts(db, u.id),
        )
        for u in users
    ]


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除一个普通用户及其全部数据（会话/消息/报告级联）。

    保护规则：管理员账号（含自己）不可被删除，防止误删权限体系。
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="管理员账号受保护，不可删除")

    # 级联删除该用户所有会话（含消息、报告）
    sessions = db.scalars(
        select(InterviewSession).where(InterviewSession.user_id == user_id)
    ).all()
    for s in sessions:
        redis_client.delete_session(s.id)
    db.query(InterviewSession).filter(InterviewSession.user_id == user_id).delete()
    db.query(IndustryReport).filter(IndustryReport.user_id == user_id).delete()
    db.query(ProjectReport).filter(ProjectReport.user_id == user_id).delete()
    db.delete(user)
    db.commit()

    logger.info("管理员 %s 删除用户 %s（%s）", current.id, user_id, user.username)
    return {"ok": True, "id": user_id}


@router.get("/sessions", response_model=list[AdminSessionItem])
def list_all_sessions(
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """所有用户的面试会话（时间倒序）。"""
    rows = db.execute(
        select(InterviewSession, User.username)
        .join(User, InterviewSession.user_id == User.id)
        .order_by(InterviewSession.id.desc())
        .limit(500)
    ).all()

    message_counts = dict(
        db.execute(
            select(ChatMessage.session_id, func.count(ChatMessage.id)).group_by(
                ChatMessage.session_id
            )
        ).all()
    )
    report_ids = set(
        db.scalars(select(InterviewReport.session_id)).all()
    )

    return [
        AdminSessionItem(
            id=s.id,
            user_id=s.user_id,
            username=username,
            job_title=s.job_title,
            interviewer_role=s.interviewer_role,
            interviewer_name=ROLE_NAMES.get(s.interviewer_role, s.interviewer_role),
            status=s.status,
            created_at=_fmt(s.created_at),
            ended_at=_fmt(s.ended_at),
            message_count=message_counts.get(s.id, 0),
            has_report=s.id in report_ids,
        )
        for s, username in rows
    ]


@router.delete("/sessions/{session_id}")
def delete_any_session(
    session_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除任意一场面试会话（消息/报告级联，Redis 缓存同步清理）。"""
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.query(InterviewReport).filter(InterviewReport.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    redis_client.delete_session(session_id)

    logger.info("管理员 %s 删除会话 %s", current.id, session_id)
    return {"ok": True, "session_id": session_id}
