from dataclasses import dataclass, field
import json
import logging
import time
from typing import Any

import requests


@dataclass
class Message:
    role: str
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_call_id: str = ""


class GLMClient:
    MAX_RETRIES = 3
    RETRY_BACKOFF = (2, 5, 10)

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._is_minimax = "minimax" in base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        self.logger = logging.getLogger("coleague.llm")

    def _post(self, payload: dict) -> dict:
        url = self.base_url if self.base_url.endswith(("/completions", "/chatcompletion_v2")) \
            else f"{self.base_url}/chat/completions"
        if self._is_minimax:
            payload.setdefault("reasoning_split", True)
        for attempt in range(self.MAX_RETRIES + 1):
            response = self.session.post(url, json=payload)
            if response.status_code in (429, 529) and attempt < self.MAX_RETRIES:
                wait = self.RETRY_BACKOFF[attempt]
                self.logger.warning(f"限流 {response.status_code}，{wait}s 后重试 ({attempt + 1}/{self.MAX_RETRIES})")
                time.sleep(wait)
                continue
            if not response.ok:
                self.logger.error(f"LLM API 错误 {response.status_code}: {response.text[:500]}")
            response.raise_for_status()
            # MiniMax 错误响应可能包含多行 JSON，只取第一行
            text = response.text.strip()
            data = json.loads(text.split("\n", 1)[0])
            if data.get("type") == "error":
                err = data.get("error", {})
                msg = err.get("message", "")
                # MiniMax 过载(2064)：HTTP 200 但 body 报错，需重试
                if "2064" in msg and attempt < self.MAX_RETRIES:
                    wait = self.RETRY_BACKOFF[attempt]
                    self.logger.warning(f"MiniMax 过载，{wait}s 后重试 ({attempt + 1}/{self.MAX_RETRIES})")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"LLM API 错误: {msg or text[:200]}")
            self._log_usage(data)
            return data
        raise RuntimeError("LLM API 重试次数耗尽")

    def chat(self, messages: list[Message], **kwargs: Any) -> str:
        payload = {
            "model": self.model,
            "messages": [self._serialize(m) for m in messages],
            **kwargs,
        }
        data = self._post(payload)
        return data["choices"][0]["message"]["content"]

    def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [self._serialize(m) for m in messages],
            "tools": tools,
        }
        data = self._post(payload)
        return data["choices"][0]["message"]

    def _log_usage(self, data: dict[str, Any]) -> None:
        usage = data.get("usage", {})
        if usage:
            self.logger.info(
                f"token用量 prompt={usage.get('prompt_tokens', '?')} "
                f"completion={usage.get('completion_tokens', '?')} "
                f"total={usage.get('total_tokens', '?')}"
            )

    def _serialize(self, m: Message) -> dict[str, Any]:
        d: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.tool_calls:
            d["tool_calls"] = m.tool_calls
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        return d
