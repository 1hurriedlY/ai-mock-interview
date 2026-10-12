"""项目渠道 / 讲项目话术路由。

- POST /api/project/channels     生成求职/接单渠道平台清单 → 入库 project_reports(type=channels)
- POST /api/project/script       {project_name, description?} STAR 法生成讲项目话术 → 入库(type=script)
- GET  /api/project/history      当前用户渠道/话术历史列表（时间倒序）
- GET  /api/project/history/{id} 单条记录完整内容
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import ProjectReport, User
from ..services.ai_config_service import resolve_config
from ..services.agents.project_agent import ProjectAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# type 枚举：渠道清单 / 讲项目话术
TYPE_CHANNELS = "channels"
TYPE_SCRIPT = "script"


# ---------- 请求 / 响应模型 ----------
class ScriptRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=255, description="项目名称")
    description: str = Field(default="", max_length=2000, description="项目描述（可选）")


class ProjectSummary(BaseModel):
    """历史列表项：概要。"""

    id: int
    type: str  # channels / script
    project_name: Optional[str] = None  # 话术的项目名；渠道清单为 None
    summary: str  # 内容概要预览
    created_at: str


class ProjectDetail(BaseModel):
    """单条记录完整内容。"""

    id: int
    type: str
    project_name: Optional[str] = None
    content: dict
    created_at: str


# ---------- 内部工具 ----------
def _fmt(dt) -> str:
    """时间格式化为字符串。"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def _load_content(raw: str) -> dict:
    """content 字段（JSON 字符串）转 dict。"""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _content_preview(content: dict, type_: str) -> str:
    """从内容里抽一句预览：渠道清单取 summary，话术取电梯介绍。"""
    if type_ == TYPE_SCRIPT:
        return (content.get("summary") or "")[:80]
    return (content.get("summary") or "")[:80]


# ---------- 路由 ----------
@router.post("/channels")
def generate_channels(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成求职/接单渠道平台清单并入库。"""
    try:
        content = ProjectAgent(resolve_config(db, current.id)).generate_channels()
    except Exception as exc:
        logger.exception("渠道清单 Agent 调用失败")
        raise HTTPException(status_code=502, detail=f"生成渠道清单失败：{exc}")

    report = ProjectReport(
        user_id=current.id,
        type=TYPE_CHANNELS,
        content=json.dumps(content, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return ProjectDetail(
        id=report.id,
        type=report.type,
        project_name=None,
        content=_load_content(report.content),
        created_at=_fmt(report.created_at),
    )


@router.post("/script")
def generate_script(
    body: ScriptRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用 STAR 法生成讲项目面试话术并入库。"""
    project_name = body.project_name.strip()
    if not project_name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    try:
        content = ProjectAgent(resolve_config(db, current.id)).generate_script(project_name, body.description)
    except Exception as exc:
        logger.exception("讲项目话术 Agent 调用失败")
        raise HTTPException(status_code=502, detail=f"生成话术失败：{exc}")

    report = ProjectReport(
        user_id=current.id,
        type=TYPE_SCRIPT,
        project_name=content.get("project_name") or project_name,
        content=json.dumps(content, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return ProjectDetail(
        id=report.id,
        type=report.type,
        project_name=report.project_name,
        content=_load_content(report.content),
        created_at=_fmt(report.created_at),
    )


@router.get("/history", response_model=list[ProjectSummary])
def list_project_history(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户的渠道/话术历史列表（时间倒序）。"""
    reports = db.scalars(
        select(ProjectReport)
        .where(ProjectReport.user_id == current.id)
        .order_by(ProjectReport.created_at.desc(), ProjectReport.id.desc())
    ).all()

    return [
        ProjectSummary(
            id=r.id,
            type=r.type,
            project_name=r.project_name,
            summary=_content_preview(_load_content(r.content), r.type),
            created_at=_fmt(r.created_at),
        )
        for r in reports
    ]


@router.get("/history/{report_id}", response_model=ProjectDetail)
def get_project_detail(
    report_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """单条渠道/话术记录完整内容。"""
    report = db.get(ProjectReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    if report.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权访问该记录")

    return ProjectDetail(
        id=report.id,
        type=report.type,
        project_name=report.project_name,
        content=_load_content(report.content),
        created_at=_fmt(report.created_at),
    )


@router.delete("/history/{report_id}")
def delete_project_history(
    report_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除一条渠道/话术历史记录。"""
    report = db.get(ProjectReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    if report.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权删除该记录")

    db.delete(report)
    db.commit()

    logger.info("用户 %s 删除求职工具记录 %s（type=%s）", current.id, report_id, report.type)
    return {"ok": True, "id": report_id}
