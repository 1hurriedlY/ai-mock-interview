"""简历路由：上传 PDF/DOCX，解析并调用简历分析 Agent，缓存结果。

返回结构：
{
  "resume_id": 缓存 key（按内容哈希，同简历不重复分析）,
  "analysis": { summary/skills/projects/highlights/education },
  "text_preview": 前 500 字简历原文（供前端确认解析是否成功）
}
"""
import hashlib
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import config
from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..redis_client import redis_client
from ..services.ai_config_service import resolve_config
from ..services.agents.resume_agent import ResumeAgent
from ..services.resume_parser import extract_text

logger = logging.getLogger(__name__)

router = APIRouter()

# 允许的简历扩展名
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
# 单文件大小上限 10MB
MAX_SIZE = 10 * 1024 * 1024


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(..., description="简历文件（pdf/docx/txt）"),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """上传简历：解析 → 分析 → 缓存。重复上传同一文件直接返回缓存。"""
    suffix = _safe_suffix(file.filename or "")
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"不支持的简历格式：{suffix}，仅支持 pdf/docx/txt")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="文件超过 10MB 上限")

    # 内容哈希作为缓存 key，同简历不重复调用大模型
    resume_id = hashlib.sha256(content).hexdigest()[:16]
    cached = redis_client.get_resume_analysis(resume_id)
    if cached:
        return {"resume_id": resume_id, "analysis": cached, "from_cache": True}

    # 保存文件到 uploads（便于排查，不强制）
    try:
        file_path = config.UPLOAD_DIR / f"{resume_id}{suffix}"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
    except Exception as exc:
        logger.warning("保存简历文件失败（不影响流程）：%s", exc)

    # 抽取文本
    try:
        from pathlib import Path

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            text = extract_text(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("简历解析失败")
        raise HTTPException(status_code=500, detail=f"简历解析失败：{exc}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="未能从文件中提取到文本，请确认文件内容")

    # 调用简历分析 Agent
    try:
        analysis = ResumeAgent(resolve_config(db, current.id)).analyze(text)
    except Exception as exc:
        logger.exception("简历分析 Agent 调用失败")
        raise HTTPException(status_code=502, detail=f"简历分析失败：{exc}")

    # 缓存分析结果（含原文用于构造题卡）
    cache_payload = {**analysis, "_text": text[:12000]}
    redis_client.set_resume_analysis(resume_id, cache_payload)

    return {
        "resume_id": resume_id,
        "analysis": analysis,
        "text_preview": text[:500],
        "from_cache": False,
    }


def _safe_suffix(filename: str) -> str:
    """取小写扩展名；无扩展名返回空串。"""
    idx = filename.rfind(".")
    if idx == -1:
        return ""
    return filename[idx:].lower()
