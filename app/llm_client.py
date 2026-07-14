"""
封装对通义千问（DashScope OpenAI 兼容模式）的调用。
只负责"发提示词、拿到JSON"这一层，不关心具体是T1的哪个接口。
"""
import json
import logging
import re

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


class LlmCallError(Exception):
    """大模型调用失败或者返回内容无法解析成合法JSON时抛出，由上层决定是否走fallback。"""


class LlmClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            timeout=settings.llm_timeout_seconds,
        )
        self._model = settings.dashscope_model
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens
        self._max_retries = settings.llm_max_retries

    def call_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        调用大模型，要求返回一个JSON对象。
        自动重试 self._max_retries 次；全部失败则抛出 LlmCallError，由上层走 fallback。
        """
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    response_format={"type": "json_object"},
                )
                raw_text = response.choices[0].message.content
                return self._parse_json(raw_text)
            except Exception as exc:  # noqa: BLE001 - 这里统一捕获，交给上层决定fallback
                last_error = exc
                logger.warning("LLM call failed (attempt %s/%s): %s", attempt + 1, self._max_retries + 1, exc)
        raise LlmCallError(f"LLM调用最终失败: {last_error}") from last_error

    @staticmethod
    def _parse_json(raw_text: str | None) -> dict:
        if not raw_text or not raw_text.strip():
            raise LlmCallError("大模型返回了空内容")

        text = raw_text.strip()

        # 有些模型即使要求了json_object，偶尔还是会带markdown代码块围栏，这里做一层兜底清理
        if text.startswith("```"):
            text = re.sub(r"^```(json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # 再兜底一次：截取第一个 { 到最后一个 } 之间的内容再解析一次
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise LlmCallError(f"大模型返回内容不是合法JSON: {exc}") from exc


_llm_client: LlmClient | None = None


def get_llm_client() -> LlmClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LlmClient()
    return _llm_client
