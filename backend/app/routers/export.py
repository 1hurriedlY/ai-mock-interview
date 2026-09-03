"""报告导出路由：导出评分报告为 DOCX / PDF，并提供下载。

- POST /api/report/{report_id}/export?format=docx|pdf   渲染文件并返回下载 URL
- GET  /api/report/{report_id}/download?format=docx|pdf  下载已生成的文件（幂等）

权限：报告归属当前用户才可导出/下载；找不到报告返回 404，格式非法返回 400。
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import InterviewReport, InterviewSession, User
from ..services import export_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 支持的导出格式
VALID_FORMATS = {"docx", "pdf"}


def _report_or_404(
    db: Session, report_id: int, user: User
) -> tuple[InterviewReport, InterviewSession]:
    """查报告 + 所属会话；不存在返回 404，归属他人返回 403。"""
    report = db.get(InterviewReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    session = db.get(InterviewSession, report.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="报告关联的会话不存在")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该报告")
    return report, session


@router.post("/{report_id}/export")
def export_report(
    report_id: int,
    format: str = "docx",
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """渲染报告为指定格式文件并落盘，返回下载 URL。"""
    fmt = (format or "docx").lower()
    if fmt not in VALID_FORMATS:
        raise HTTPException(
            status_code=400, detail=f"不支持的导出格式：{format}，仅支持 docx / pdf"
        )

    report, session = _report_or_404(db, report_id, current)

    try:
        info = export_service.write_export(report, session, fmt)
    except Exception as exc:
        logger.exception("导出失败：report_id=%s format=%s", report_id, fmt)
        raise HTTPException(status_code=500, detail=f"导出失败：{exc}")

    return info


@router.get("/{report_id}/file")
def file_report(
    report_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_format: str = Header(default="docx", alias="X-Export-Format"),
) -> FileResponse:
    """下载报告文件（中性 URL：无扩展名、无附件头，避免浏览器下载管理器/IDM 抢先接管）。

    格式通过 X-Export-Format 请求头传递（docx/pdf），路径不带 .pdf/.docx 后缀。
    """
    fmt = (x_format or "docx").lower()
    if fmt not in VALID_FORMATS:
        raise HTTPException(
            status_code=400, detail=f"不支持的导出格式：{x_format}，仅支持 docx / pdf"
        )

    report, session = _report_or_404(db, report_id, current)

    path = export_service.export_path(report.id, fmt)
    if not path.exists():
        # 文件被清理过则重新生成
        try:
            export_service.write_export(report, session, fmt)
        except Exception as exc:
            logger.exception("生成下载文件失败：%s", exc)
            raise HTTPException(status_code=500, detail=f"生成下载文件失败：{exc}")

    return FileResponse(
        path=str(path),
        media_type=_media_type(fmt),
    )


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    format: str = "docx",
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """下载已生成的报告文件（不存在则现场生成，保证幂等）。"""
    fmt = (format or "docx").lower()
    if fmt not in VALID_FORMATS:
        raise HTTPException(
            status_code=400, detail=f"不支持的导出格式：{format}，仅支持 docx / pdf"
        )

    report, session = _report_or_404(db, report_id, current)

    path = export_service.export_path(report.id, fmt)
    if not path.exists():
        # 文件被清理过则重新生成
        try:
            export_service.write_export(report, session, fmt)
        except Exception as exc:
            logger.exception("生成下载文件失败：%s", exc)
            raise HTTPException(status_code=500, detail=f"生成下载文件失败：{exc}")

    # 注意：不传 filename（不加 Content-Disposition: attachment）。
    # Chrome 对带附件头的 fetch 会直接走"下载"并拒绝交给 XHR（ERR_BLOCKED_BY_CLIENT），
    # 前端用 blob + <a download> 方式保存并在 JS 侧命名，效果一致。
    return FileResponse(
        path=str(path),
        media_type=_media_type(fmt),
    )


def _media_type(fmt: str) -> str:
    """按格式返回 MIME。"""
    if fmt == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/pdf"
