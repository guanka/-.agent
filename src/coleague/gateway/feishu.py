"""飞书网关客户端"""

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class FeishuMessage:
    msg_type: str
    content: dict[str, Any]
    open_id: str | None = None
    union_id: str | None = None


class FeishuGateway:
    def __init__(self, webhook_url: str, secret: str | None = None):
        self.webhook_url = webhook_url
        self.secret = secret
        self.session = requests.Session()

    def send_message(self, message: FeishuMessage) -> dict[str, Any]:
        payload = {
            "msg_type": message.msg_type,
            "content": message.content,
        }
        if message.open_id:
            payload["open_id"] = message.open_id
        if message.union_id:
            payload["union_id"] = message.union_id

        response = self.session.post(self.webhook_url, json=payload)
        response.raise_for_status()
        return response.json()

    def send_text(self, text: str, open_id: str | None = None) -> dict[str, Any]:
        message = FeishuMessage(
            msg_type="text",
            content={"text": text},
            open_id=open_id,
        )
        return self.send_message(message)
