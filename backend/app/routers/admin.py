"""管理员路由：查看与管理所有账号及其数据（仅 is_admin 可访问）。

- GET    /api/admin/users          所有用户列表（含各自数据量统计）
- DELETE /api/admin/users/{id}     删除某用户及其全部数据（管理员账号受保护）
- GET    /api/admin/sessions       所有用户的面试会话（含所属用户名）
- GET    /api/admin/sessions/{id}  任一会话完整详情（问答 + 报告，供管理审阅）
- DELETE /api/admin/sessions/{id}  删除任意一场面试会话（级联消息/报告）
- GET/DELETE /api/admin/industry     全局行业调研记录
- GET/DELETE /api/admin/project      全局求职渠道/话术记录
"""
import json
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
    MemberOrder,
    MembershipCode,
    ProjectReport,
    User,
)
from ..redis_client import redis_client
from ..services.agents.question_agent import ROLE_NAMES
from ..services.membership_service import generate_codes as _gen_codes
from ..services.membership_service import grant_days, is_member

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


class AdminSessionDetail(BaseModel):
    """管理端：任一会话完整详情（问答 + 报告 + 所属用户）。"""

    id: int
    user_id: int
    username: str
    job_title: str
    interviewer_role: str
    interviewer_name: str
    status: str
    created_at: str
    ended_at: Optional[str] = None
    resume_text: Optional[str] = None
    messages: list[dict]
    report: Optional[dict] = None


class AdminIndustryItem(BaseModel):
    """全局行业调研记录。"""

    id: int
    user_id: int
    username: str
    industry_name: str
    content_preview: str
    created_at: str


class AdminProjectItem(BaseModel):
    """全局求职渠道 / 讲项目话术记录。"""

    id: int
    user_id: int
    username: str
    type: str
    project_name: str
    content_preview: str
    created_at: str


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
    # 会员数据：删除订单，兑换码解绑（无库级外键，业务层兜底）
    db.query(MemberOrder).filter(MemberOrder.user_id == user_id).delete()
    db.query(MembershipCode).filter(MembershipCode.used_by == user_id).update(
        {"used_by": None, "used_at": None}, synchronize_session=False
    )
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


@router.get("/sessions/{session_id}", response_model=AdminSessionDetail)
def get_any_session_detail(
    session_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理审阅：任一会话的完整问答与报告内容。"""
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    user = db.get(User, session.user_id)

    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
    ).all()
    report = db.scalar(
        select(InterviewReport).where(InterviewReport.session_id == session_id)
    )

    return AdminSessionDetail(
        id=session.id,
        user_id=session.user_id,
        username=user.username if user else f"#{session.user_id}",
        job_title=session.job_title,
        interviewer_role=session.interviewer_role,
        interviewer_name=ROLE_NAMES.get(session.interviewer_role, session.interviewer_role),
        status=session.status,
        created_at=_fmt(session.created_at),
        ended_at=_fmt(session.ended_at),
        resume_text=session.resume_text,
        messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "reference": m.reference,
                "created_at": _fmt(m.created_at),
            }
            for m in messages
        ],
        report=_report_full(report),
    )


@router.get("/industry", response_model=list[AdminIndustryItem])
def list_all_industry(
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """所有用户的行业调研记录（时间倒序）。"""
    rows = db.execute(
        select(IndustryReport, User.username)
        .join(User, IndustryReport.user_id == User.id)
        .order_by(IndustryReport.id.desc())
        .limit(500)
    ).all()
    return [
        AdminIndustryItem(
            id=r.id,
            user_id=r.user_id,
            username=username,
            industry_name=r.industry_name,
            content_preview=_preview_json(r.content, 90),
            created_at=_fmt(r.created_at),
        )
        for r, username in rows
    ]


@router.delete("/industry/{report_id}")
def delete_any_industry(
    report_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除任意一份行业调研记录。"""
    report = db.get(IndustryReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(report)
    db.commit()
    logger.info("管理员 %s 删除行业调研 %s", current.id, report_id)
    return {"ok": True, "id": report_id}


@router.get("/project", response_model=list[AdminProjectItem])
def list_all_project(
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """所有用户的求职渠道 / 讲项目话术记录（时间倒序）。"""
    rows = db.execute(
        select(ProjectReport, User.username)
        .join(User, ProjectReport.user_id == User.id)
        .order_by(ProjectReport.id.desc())
        .limit(500)
    ).all()
    return [
        AdminProjectItem(
            id=r.id,
            user_id=r.user_id,
            username=username,
            type=r.type,
            project_name=r.project_name or "",
            content_preview=_preview_json(r.content, 90),
            created_at=_fmt(r.created_at),
        )
        for r, username in rows
    ]


@router.delete("/project/{report_id}")
def delete_any_project(
    report_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除任意一份求职渠道 / 话术记录。"""
    report = db.get(ProjectReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(report)
    db.commit()
    logger.info("管理员 %s 删除求职记录 %s", current.id, report_id)
    return {"ok": True, "id": report_id}


# ---------- 详情序列化 ----------
def _report_full(report: InterviewReport | None) -> dict | None:
    """报告完整 JSON（审阅详情用），与 history 详情同构。"""
    if report is None:
        return None

    def _load(raw, default):
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
        "qna": _load(report.qna, []),
        "created_at": _fmt(report.created_at),
    }


def _preview_json(raw: str | None, limit: int) -> str:
    """JSON 字符串的纯文本预览（剔除结构符，截取前 limit 字）。"""
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
        text = parsed if isinstance(parsed, str) else json.dumps(parsed, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        text = raw
    text = " ".join(text.split())
    return text[:limit] + ("…" if len(text) > limit else "")


# ---------- 会员管理 ----------
@router.get("/members")
def list_members(
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """所有用户会员状态与额度（会员管理页用）。"""
    users = db.scalars(select(User).order_by(User.id.asc())).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "is_member": is_member(u),
            "member_until": _fmt(u.member_until),
            "free_interview_used": u.free_quota_used or 0,
            "export_quota_used": u.export_quota_used or 0,
        }
        for u in users
    ]


@router.post("/members/users/{user_id}/grant")
def grant_member_days(
    user_id: int,
    body: dict,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """手动为用户开通/顺延会员（days：天数，1~3650）。"""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    days = int((body or {}).get("days", 30) or 30)
    if not (1 <= days <= 3650):
        raise HTTPException(status_code=400, detail="开通天数需在 1~3650 之间")
    grant_days(user, days)
    db.commit()
    logger.info("管理员 %s 为用户 %s 开通会员 %s 天", current.id, user_id, days)
    return {"ok": True, "id": user_id, "member_until": _fmt(user.member_until)}


@router.get("/members/codes")
def list_codes(
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """兑换码列表（含使用状态）。"""
    rows = db.execute(
        select(MembershipCode, User.username)
        .outerjoin(User, MembershipCode.used_by == User.id)
        .order_by(MembershipCode.id.desc())
        .limit(200)
    ).all()
    return [
        {
            "id": c.id,
            "code": c.code,
            "grant_days": c.grant_days,
            "used": c.used_by is not None,
            "used_by": username or "",
            "used_at": _fmt(c.used_at),
            "created_at": _fmt(c.created_at),
        }
        for c, username in rows
    ]


@router.post("/members/codes/generate")
def make_codes(
    body: dict,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """批量生成兑换码。body: {count:10, days:30}。"""
    count = max(1, min(int((body or {}).get("count", 10) or 10), 100))
    days = max(1, min(int((body or {}).get("days", 30) or 30), 3650))
    codes = _gen_codes(db, count, days)
    logger.info("管理员 %s 生成兑换码 %s 个（%s 天）", current.id, len(codes), days)
    return {"ok": True, "count": len(codes), "days": days, "codes": codes}
