"""模型配置路由：查看 / 保存 / 清除当前用户的大模型接入配置，并提供连通性测试。

- GET    /api/ai-config       当前配置（api_key 掩码）+ 预设清单 + .env 默认值
- PUT    /api/ai-config       保存配置（api_key 传空表示保持原值）
- DELETE /api/ai-config       清除配置，回退 .env 默认
- POST   /api/ai-config/test  用提交的配置做一次连通性测试（不落库）
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config
from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..services import ai_config_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- 请求模型 ----------
class AIConfigIn(BaseModel):
    provider_type: str = Field(default="cloud", description="local（本地部署）/ cloud（云端）")
    provider: str = Field(default="custom", description="服务商标识")
    base_url: str = Field(default="", description="OpenAI 兼容接口地址")
    model: str = Field(default="", description="模型名称")
    api_key: str = Field(default="", description="API Key；留空表示保持原值")


class AIConfigTestIn(BaseModel):
    base_url: str = Field(default="")
    model: str = Field(default="")
    api_key: str = Field(default="")


# ---------- 内部工具 ----------
def _public(cfg: dict) -> dict:
    """对外输出：api_key 一律掩码，另附 has_key 便于前端提示。"""
    out = dict(cfg)
    raw = cfg.get("api_key") or ""
    out["api_key"] = svc.mask_key(raw)
    out["has_key"] = bool(raw)
    return out


def _row_to_dict(row) -> dict:
    """ORM 行转普通 dict。"""
    return {
        "provider_type": row.provider_type,
        "provider": row.provider,
        "base_url": row.base_url,
        "api_key": row.api_key,
        "model": row.model,
    }


# ---------- 路由 ----------
@router.get("")
def read_ai_config(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回当前用户的模型配置、预设清单与 .env 默认值。"""
    row = svc.get_config(db, current.id)
    return {
        "config": _public(_row_to_dict(row)) if row is not None else None,
        "using_default": row is None,
        "default": _public(svc.env_default()),
        "presets": svc.PRESETS,
    }


@router.put("")
def save_ai_config(
    body: AIConfigIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存当前用户的模型配置。"""
    try:
        row = svc.save_config(db, current.id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    logger.info("用户 %s 更新模型配置：%s / %s", current.id, row.provider, row.model)
    return {"ok": True, "config": _public(_row_to_dict(row))}


@router.delete("")
def clear_ai_config(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清除自定义配置，回退 .env 默认。"""
    removed = svc.delete_config(db, current.id)
    logger.info("用户 %s 清除模型配置（removed=%s）", current.id, removed)
    return {"ok": True, "removed": removed}


@router.post("/test")
def test_ai_config(
    body: AIConfigTestIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """连通性测试。api_key 留空时沿用已保存的 key（前端不回显明文也能测）。"""
    api_key = (body.api_key or "").strip()
    if not api_key:
        row = svc.get_config(db, current.id)
        if row is not None:
            api_key = row.api_key or ""
        if not api_key:
            api_key = config.DASHSCOPE_API_KEY

    ok, message = svc.test_connection(
        {"base_url": body.base_url, "model": body.model, "api_key": api_key}
    )
    return {"ok": ok, "message": message}
