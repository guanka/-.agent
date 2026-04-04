"""智谱 AI (GLM) 客户端"""

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class Message:
    role: str
    content: str


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

    def chat(self, messages: list[Message], **kwargs: Any) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            **kwargs,
        }
        response = self.session.post(f"{self.base_url}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
