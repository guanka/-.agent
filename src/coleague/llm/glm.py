from dataclasses import dataclass, field
import logging
from typing import Any

import requests


@dataclass
class Message:
    role: str
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_call_id: str = ""


class GLMClient:
    def __init__(
        self,
        api_key: str,
        model: str = "glm-4",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        self.logger = logging.getLogger("coleague.llm")

    def chat(self, messages: list[Message], **kwargs: Any) -> str:
        payload = {
            "model": self.model,
            "messages": [self._serialize(m) for m in messages],
            **kwargs,
        }
        response = self.session.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        self._log_usage(data)
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
        response = self.session.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        self._log_usage(data)
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
