"""Agent 基类：统一封装通义千问（DashScope OpenAI 兼容模式）的调用。

所有 Agent 继承 BaseAgent：
- chat_json：非流式，要求模型输出合法 JSON，解析后返回 dict
- chat_stream：流式生成，逐段产出文本（供面试官对话 SSE 使用）
- 失败时抛出 AgentError，由调用方决定降级策略

使用 openai 3.x SDK，兼容 DashScope 兼容模式的 base_url 与 api_key。
"""
import json
import logging
from typing import Any, Iterator

from openai import OpenAI

from ... import config

logger = logging.getLogger(__name__)


class AgentError(RuntimeError):
    """Agent 调用失败（网络、鉴权、JSON 解析等）。"""


class BaseAgent:
    """所有 Agent 的基类。子类只需定义 system_prompt 与所需方法。"""

    # 子类覆盖：当前 Agent 的角色描述（系统提示词）
    system_prompt: str = "你是一个专业的面试辅助助手。"

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        if not config.DASHSCOPE_API_KEY:
            logger.warning("DASHSCOPE_API_KEY 未配置，Agent 调用将失败")
        else:
            self._client = OpenAI(
                api_key=config.DASHSCOPE_API_KEY,
                base_url=config.DASHSCOPE_BASE_URL,
                timeout=120,
                max_retries=2,
            )

    # 生成 token 上限：默认放宽到 4096，保证行业报告/题卡/评分报告等长 JSON 不被截断；
    # 短回复场景（如面试官对话）由子类覆盖为更小值以提速。
    MAX_OUTPUT_TOKENS = 4096

    # ---------- 基础调用 ----------
    def _chat(self, messages: list[dict], *, temperature: float = 0.7,
              json_mode: bool = False) -> str:
        """非流式调用，返回文本；json_mode=True 时要求 JSON 输出。"""
        if self._client is None:
            raise AgentError("未配置 DASHSCOPE_API_KEY，无法调用大模型")
        kwargs: dict[str, Any] = {
            "model": config.DASHSCOPE_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.MAX_OUTPUT_TOKENS,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = self._client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as exc:
            logger.error("DashScope 调用失败：%s", exc)
            raise AgentError(str(exc)) from exc

    def _chat_stream(self, messages: list[dict], *, temperature: float = 0.7) -> Iterator[str]:
        """流式调用，逐段 yield 文本。"""
        if self._client is None:
            raise AgentError("未配置 DASHSCOPE_API_KEY，无法调用大模型")
        try:
            stream = self._client.chat.completions.create(
                model=config.DASHSCOPE_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=self.MAX_OUTPUT_TOKENS,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            logger.error("DashScope 流式调用失败：%s", exc)
            raise AgentError(str(exc)) from exc

    # ---------- 对外方法 ----------
    def chat(self, user_message: str, *, system: str | None = None,
             temperature: float = 0.7) -> str:
        """简单单轮对话，返回纯文本。"""
        sys_prompt = system or self.system_prompt
        return self._chat(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
        )

    def chat_json(self, user_message: str, *, system: str | None = None,
                  temperature: float = 0.2) -> dict:
        """单轮对话并要求返回 JSON 对象。解析失败会重试一次。"""
        sys_prompt = system or self.system_prompt
        content = self._chat(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            json_mode=True,
        )
        return parse_json_object(content)

    def stream(self, messages: list[dict], *, temperature: float = 0.7) -> Iterator[str]:
        """多轮上下文流式生成（面试官 Agent 使用）。"""
        return self._chat_stream(messages, temperature=temperature)


def parse_json_object(text: str) -> dict:
    """从模型输出中解析 JSON 对象；容忍被 ```json 代码块包裹或前后多余文本。"""
    cleaned = text.strip()
    # 去掉 ```json ... ``` 包裹
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # 去掉首行可能的 json 标记
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 尝试截取第一个 { 到最后一个 } 之间的内容
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise AgentError(f"模型输出不是合法 JSON：{text[:200]}")
