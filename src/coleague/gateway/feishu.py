"""飞书网关"""

from dataclasses import dataclass, field
from typing import Any, Callable

import requests


@dataclass
class FeishuMessage:
    msg_type: str
    content: dict[str, Any]
    open_id: str | None = None
    union_id: str | None = None
    chat_id: str | None = None
    message_id: str | None = None


@dataclass
class FeishuConfig:
    enabled: bool = True
    app_id: str = ""
    app_secret: str = ""
    domain: str = "feishu"
    connection_mode: str = "websocket"
    require_mention: bool = True
    dm_policy: str = "open"
    allow_from: list[str] = field(default_factory=list)
    group_allow_from: list[str] = field(default_factory=list)
    group_policy: str = "open"
    groups: dict[str, Any] = field(default_factory=dict)


class FeishuGateway:
    def __init__(self, config: FeishuConfig):
        self.config = config
        self.session = requests.Session()
        self._tenant_access_token: str | None = None

    def get_tenant_access_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token

        url = f"https://open.{self.config.domain}.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.config.app_id, "app_secret": self.config.app_secret}
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        token: str = data.get("tenant_access_token") or ""
        self._tenant_access_token = token
        return token

    def send_message(self, message: FeishuMessage) -> dict[str, Any]:
        token = self.get_tenant_access_token()
        url = f"https://open.{self.config.domain}.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": "open_id"}
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "receive_id": message.open_id,
            "msg_type": message.msg_type,
            "content": message.content,
        }

        response = self.session.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def send_text(self, text: str, open_id: str | None = None) -> dict[str, Any]:
        message = FeishuMessage(
            msg_type="text",
            content={"text": text},
            open_id=open_id,
        )
        return self.send_message(message)

    def add_reaction(self, message_id: str, emoji_type: str = "OnIt") -> str | None:
        """给消息添加表情回复，返回 reaction_id"""
        token = self.get_tenant_access_token()
        url = f"https://open.{self.config.domain}.cn/open-apis/im/v1/messages/{message_id}/reactions"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"reaction_type": {"emoji_type": emoji_type}}
        resp = self.session.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("reaction_id")

    def delete_reaction(self, message_id: str, reaction_id: str) -> None:
        """删除表情回复"""
        token = self.get_tenant_access_token()
        url = f"https://open.{self.config.domain}.cn/open-apis/im/v1/messages/{message_id}/reactions/{reaction_id}"
        headers = {"Authorization": f"Bearer {token}"}
        resp = self.session.delete(url, headers=headers)
        resp.raise_for_status()

    def upload_file(self, file_path: str, file_type: str = "stream") -> str | None:
        """上传文件到飞书，返回 file_key"""
        import os
        token = self.get_tenant_access_token()
        url = f"https://open.{self.config.domain}.cn/open-apis/im/v1/files"
        headers = {"Authorization": f"Bearer {token}"}
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            resp = self.session.post(
                url,
                headers=headers,
                data={"file_type": file_type, "file_name": file_name},
                files={"file": (file_name, f)},
            )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("file_key")

    def is_user_allowed(self, user_open_id: str | None, chat_id: str | None = None) -> bool:
        if self.config.dm_policy == "open":
            return True
        if user_open_id and user_open_id in self.config.allow_from:
            return True
        if chat_id and chat_id in self.config.group_allow_from:
            return True
        return False
