"""用户自定义模型配置：预设清单、读写、解析（用户配置优先，回退 .env 默认）、连通性测试。

设计：
- 每个用户至多一条配置（user_ai_configs 表），未配置时回退 .env 里的 DashScope 默认
- 所有 Agent 通过 resolve_config() 拿到最终生效的 {base_url, api_key, model}
- api_key 对外一律掩码返回，前端不回显明文；保存时传空字符串表示「保持原值」
"""
import logging

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..models import UserAIConfig

logger = logging.getLogger(__name__)

# ---------- 预设服务商 ----------
# 前端下拉直接消费；「自定义」项的 base_url / model 由用户手填
PRESETS: dict[str, list[dict]] = {
    "local": [
        {
            "id": "ollama",
            "name": "Ollama",
            "base_url": "http://localhost:11434/v1",
            "model": "qwen2.5:7b",
            "need_key": False,
            "hint": "本机运行 Ollama，先执行 ollama pull qwen2.5:7b",
        },
        {
            "id": "lmstudio",
            "name": "LM Studio",
            "base_url": "http://localhost:1234/v1",
            "model": "local-model",
            "need_key": False,
            "hint": "在 LM Studio 里开启本地 Server（默认 1234 端口）",
        },
        {
            "id": "vllm",
            "name": "vLLM / SGLang",
            "base_url": "http://localhost:8001/v1",
            "model": "",
            "need_key": False,
            "hint": "vLLM 默认 8000 端口与本项目后端冲突，建议换端口启动",
        },
        {
            "id": "custom",
            "name": "自定义本地服务",
            "base_url": "",
            "model": "",
            "need_key": False,
            "hint": "任何兼容 OpenAI 接口的本地推理服务",
        },
    ],
    "cloud": [
        {
            "id": "dashscope",
            "name": "通义千问（DashScope）",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "need_key": True,
            "hint": "阿里云百炼控制台获取 API Key",
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "need_key": True,
            "hint": "platform.deepseek.com 获取 API Key",
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "need_key": True,
            "hint": "需可访问 OpenAI 的网络环境",
        },
        {
            "id": "moonshot",
            "name": "月之暗面 Kimi",
            "base_url": "https://api.moonshot.cn/v1",
            "model": "moonshot-v1-8k",
            "need_key": True,
            "hint": "platform.moonshot.cn 获取 API Key",
        },
        {
            "id": "zhipu",
            "name": "智谱 GLM",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4-flash",
            "need_key": True,
            "hint": "open.bigmodel.cn 获取 API Key",
        },
        {
            "id": "custom",
            "name": "自定义云端服务",
            "base_url": "",
            "model": "",
            "need_key": True,
            "hint": "任何兼容 OpenAI 接口的云端服务",
        },
    ],
}


def mask_key(key: str) -> str:
    """API Key 掩码：保留头 3 位与末 4 位，中间用 * 代替。"""
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}{'*' * 6}{key[-4:]}"


def env_default() -> dict:
    """从 .env 读到的全局默认配置（用户未自定义时使用）。"""
    return {
        "provider_type": "cloud",
        "provider": "dashscope",
        "base_url": config.DASHSCOPE_BASE_URL,
        "api_key": config.DASHSCOPE_API_KEY,
        "model": config.DASHSCOPE_MODEL,
        "source": "env",
    }


def get_config(db: Session, user_id: int) -> UserAIConfig | None:
    """读取用户的模型配置行（未配置返回 None）。"""
    return db.scalar(select(UserAIConfig).where(UserAIConfig.user_id == user_id))


def resolve_config(db: Session, user_id: int) -> dict:
    """解析最终生效的模型配置：用户自定义优先，未配置回退 .env 默认。

    返回值供 BaseAgent 直接使用：{base_url, api_key, model, ...}
    """
    row = get_config(db, user_id)
    if row is None:
        return env_default()
    return {
        "provider_type": row.provider_type,
        "provider": row.provider,
        "base_url": row.base_url,
        "api_key": row.api_key,
        "model": row.model,
        "source": "user",
    }


def save_config(db: Session, user_id: int, data: dict) -> UserAIConfig:
    """保存（新建或更新）用户的模型配置。

    api_key 传空字符串表示「保持原值不变」——避免前端拿到掩码后回存把真实 key 冲掉。
    """
    provider_type = (data.get("provider_type") or "cloud").strip()
    if provider_type not in ("local", "cloud"):
        provider_type = "cloud"
    provider = (data.get("provider") or "custom").strip() or "custom"
    base_url = (data.get("base_url") or "").strip()
    model = (data.get("model") or "").strip()
    api_key = data.get("api_key")

    if not base_url:
        raise ValueError("接口地址不能为空")
    if not model:
        raise ValueError("模型名称不能为空")

    row = get_config(db, user_id)
    if row is None:
        row = UserAIConfig(
            user_id=user_id,
            provider_type=provider_type,
            provider=provider,
            base_url=base_url,
            api_key=(api_key or "").strip(),
            model=model,
        )
        db.add(row)
    else:
        row.provider_type = provider_type
        row.provider = provider
        row.base_url = base_url
        row.model = model
        # 传空 = 不改动已有 key
        if api_key is not None and str(api_key).strip():
            row.api_key = str(api_key).strip()
    db.commit()
    db.refresh(row)
    return row


def delete_config(db: Session, user_id: int) -> bool:
    """删除用户自定义配置（回到 .env 默认）。返回是否确实删除了记录。"""
    row = get_config(db, user_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def test_connection(cfg: dict) -> tuple[bool, str]:
    """用给定配置发一次极简请求，验证连通性与鉴权。返回 (是否成功, 提示文案)。"""
    base_url = (cfg.get("base_url") or "").strip()
    model = (cfg.get("model") or "").strip()
    if not base_url or not model:
        return False, "接口地址与模型名称不能为空"
    api_key = (cfg.get("api_key") or "").strip()
    try:
        client = OpenAI(
            # 本地部署通常不校验 key，但 SDK 要求非空，占位即可
            api_key=api_key or "not-needed",
            base_url=base_url,
            timeout=20,
            max_retries=0,
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
            temperature=0,
        )
        got = (resp.choices[0].message.content or "").strip()
        return True, f"连接成功，模型已响应：{got[:40] or '(空)'}"
    except Exception as exc:  # noqa: BLE001  对外只回一句可读原因
        logger.warning("模型连通性测试失败：%s", exc)
        return False, f"连接失败：{exc}"
