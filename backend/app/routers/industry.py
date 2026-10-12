"""行业调研路由：陌生行业结构化报告 + 历史回看。

- POST /api/industry/research    {industry_name} → 生成行业报告并入库
- GET  /api/industry/history     当前用户行业报告列表（时间倒序）
- GET  /api/industry/history/{id} 单份报告详情
"""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import IndustryReport, User
from ..services.ai_config_service import resolve_config
from ..services.agents.industry_agent import IndustryAgent

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- 请求 / 响应模型 ----------
class ResearchRequest(BaseModel):
    industry_name: str = Field(min_length=1, max_length=100, description="要调研的行业名称")


class IndustrySummary(BaseModel):
    """行业报告列表项：概要，不含正文明细。"""

    id: int
    industry_name: str
    overview: str  # 报告一句话概览（列表页预览）
    created_at: str


class IndustryDetail(BaseModel):
    """单份行业报告完整内容。"""

    id: int
    industry_name: str
    content: dict  # 完整结构化报告
    created_at: str


# ---------- 内部工具 ----------
def _fmt(dt) -> str:
    """时间格式化为字符串。"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def _load_content(raw: str) -> dict:
    """报告 content 字段（JSON 字符串）转 dict。"""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# ---------- 路由 ----------
@router.post("/research", response_model=IndustryDetail)
def research_industry(
    body: ResearchRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """对陌生行业做结构化调研，生成报告并入库。"""
    industry_name = body.industry_name.strip()
    if not industry_name:
        raise HTTPException(status_code=400, detail="行业名称不能为空")

    # 调用行业调研 Agent 生成结构化报告
    try:
        content = IndustryAgent(resolve_config(db, current.id)).research(industry_name)
    except Exception as exc:
        logger.exception("行业调研 Agent 调用失败")
        raise HTTPException(status_code=502, detail=f"行业调研失败：{exc}")

    report = IndustryReport(
        user_id=current.id,
        industry_name=content.get("industry") or industry_name,
        content=json.dumps(content, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return IndustryDetail(
        id=report.id,
        industry_name=report.industry_name,
        content=_load_content(report.content),
        created_at=_fmt(report.created_at),
    )


@router.get("/history", response_model=list[IndustrySummary])
def list_industry_history(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户的行业调研报告列表（时间倒序），带概览预览。"""
    reports = db.scalars(
        select(IndustryReport)
        .where(IndustryReport.user_id == current.id)
        .order_by(IndustryReport.created_at.desc(), IndustryReport.id.desc())
    ).all()

    result = []
    for r in reports:
        content = _load_content(r.content)
        result.append(
            IndustrySummary(
                id=r.id,
                industry_name=r.industry_name,
                overview=content.get("overview") or "",
                created_at=_fmt(r.created_at),
            )
        )
    return result


@router.get("/history/{report_id}", response_model=IndustryDetail)
def get_industry_detail(
    report_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """单份行业报告完整内容。"""
    report = db.get(IndustryReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="行业报告不存在")
    if report.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权访问该报告")

    return IndustryDetail(
        id=report.id,
        industry_name=report.industry_name,
        content=_load_content(report.content),
        created_at=_fmt(report.created_at),
    )


@router.delete("/history/{report_id}")
def delete_industry_history(
    report_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除一份行业调研历史报告。"""
    report = db.get(IndustryReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="行业报告不存在")
    if report.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权删除该报告")

    db.delete(report)
    db.commit()

    logger.info("用户 %s 删除行业报告 %s", current.id, report_id)
    return {"ok": True, "id": report_id}
