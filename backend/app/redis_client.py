"""Redis 客户端封装：会话上下文、简历分析、题卡与阶段缓存。

设计原则：
- Redis 是加速层，不是唯一数据源。所有操作 try/except，
  一旦 Redis 不可用自动降级到 MySQL，不让它阻塞主流程。
- 会话上下文按"最近 N 条消息"存储，构造 prompt 时直接读取。
"""
import json
import logging
from typing import Any, Optional

import redis

from . import config

logger = logging.getLogger(__name__)

# 会话上下文保留的最大消息条数（ring buffer 上限）
CONTEXT_MAX_MESSAGES = 20
# 各类键的过期时间（秒）
SESSION_TTL = 60 * 60 * 2      # 会话上下文 2 小时
RESUME_TTL = 60 * 60 * 24      # 简历分析结果 24 小时


class RedisClient:
    """Redis 连接的薄封装，全部方法内部兜底降级。"""

    def __init__(self) -> None:
        self._client: Optional[redis.Redis] = None
        try:
            # protocol=2：兼容 Redis <6.0（老版本不支持 RESP3 的 HELLO 命令）
            self._client = redis.Redis.from_url(
                config.REDIS_URL, decode_responses=True, protocol=2
            )
            # 启动时探活一次
            self._client.ping()
        except Exception as exc:  # pragma: no cover
            logger.warning("Redis 连接失败，将降级为仅 MySQL：%s", exc)
            self._client = None

    @property
    def available(self) -> bool:
        """Redis 是否可用。"""
        return self._client is not None

    def _safe(self, fn: Any, default: Any = None) -> Any:
        """执行 Redis 命令，失败时返回默认值并记录日志。"""
        if not self._client:
            return default
        try:
            return fn()
        except Exception as exc:
            logger.warning("Redis 操作失败：%s", exc)
            return default

    # ---------- 会话上下文 ----------
    def set_session_context(self, session_id: int, messages: list[dict]) -> None:
        """保存会话上下文（最近 N 条消息）。"""
        payload = json.dumps(messages[-CONTEXT_MAX_MESSAGES:], ensure_ascii=False)
        self._safe(lambda: self._client.setex(f"session:{session_id}", SESSION_TTL, payload))

    def get_session_context(self, session_id: int) -> Optional[list[dict]]:
        """读取会话上下文；无缓存时返回 None（调用方回退查 MySQL）。"""
        raw = self._safe(lambda: self._client.get(f"session:{session_id}"))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None

    def push_session_message(self, session_id: int, role: str, content: str) -> None:
        """在既有上下文上追加一条消息，再写回。"""
        ctx = self.get_session_context(session_id) or []
        ctx.append({"role": role, "content": content})
        self.set_session_context(session_id, ctx)

    # ---------- 简历分析结果 ----------
    def set_resume_analysis(self, resume_id: str, result: dict) -> None:
        self._safe(lambda: self._client.setex(
            f"resume:{resume_id}", RESUME_TTL, json.dumps(result, ensure_ascii=False)
        ))

    def get_resume_analysis(self, resume_id: str) -> Optional[dict]:
        raw = self._safe(lambda: self._client.get(f"resume:{resume_id}"))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None

    # ---------- 题卡与阶段推进 ----------
    def set_stage(self, session_id: int, stage: str) -> None:
        """记录当前题卡阶段。"""
        self._safe(lambda: self._client.setex(f"session:{session_id}:stage", SESSION_TTL, stage))

    def get_stage(self, session_id: int) -> Optional[str]:
        return self._safe(lambda: self._client.get(f"session:{session_id}:stage"))

    def set_question_card(self, session_id: int, card: dict) -> None:
        """保存面试题卡。"""
        self._safe(lambda: self._client.setex(
            f"session:{session_id}:card", SESSION_TTL, json.dumps(card, ensure_ascii=False)
        ))

    def get_question_card(self, session_id: int) -> Optional[dict]:
        raw = self._safe(lambda: self._client.get(f"session:{session_id}:card"))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None

    # ---------- 会话元信息（简历摘要、面试官人设等） ----------
    def set_session_meta(self, session_id: int, meta: dict) -> None:
        """保存会话级元信息（如 resume_summary）。"""
        self._safe(lambda: self._client.setex(
            f"session:{session_id}:meta", SESSION_TTL, json.dumps(meta, ensure_ascii=False)
        ))

    def get_session_meta(self, session_id: int) -> Optional[dict]:
        raw = self._safe(lambda: self._client.get(f"session:{session_id}:meta"))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None

    def delete_session(self, session_id: int) -> None:
        """会话结束后清理相关键。"""
        self._safe(lambda: self._client.delete(
            f"session:{session_id}",
            f"session:{session_id}:stage",
            f"session:{session_id}:card",
            f"session:{session_id}:meta",
        ))


# 全局单例
redis_client = RedisClient()
