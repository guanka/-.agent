"""飞书 WebSocket 服务"""

import json
import logging
import signal
import sys
from typing import Callable

import requests

from coleague.gateway import FeishuConfig, FeishuGateway


class FeishuWSService:
    def __init__(
        self,
        config: FeishuConfig,
        message_handler: Callable[[str, str | None], str],
    ):
        self.config = config
        self.message_handler = message_handler
        self.logger = logging.getLogger("coleague.feishu.ws")
        self.feishu_gateway = FeishuGateway(config)
        self.running = False

    def start(self) -> None:
        self.logger.info("启动飞书 WebSocket 服务")
        
        from lark_oapi.ws import Client
        from lark_oapi.event.dispatcher_handler import EventDispatcherHandler

        event_handler = (
            EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._on_message)
            .build()
        )

        self.ws_client = Client(
            app_id=self.config.app_id,
            app_secret=self.config.app_secret,
            event_handler=event_handler,
        )

        def signal_handler(sig, frame):
            self.logger.info("收到退出信号")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.running = True
        self.logger.info("飞书 WebSocket 服务已启动")
        self.ws_client.start()

    def stop(self) -> None:
        self.running = False
        self.logger.info("飞书 WebSocket 服务已停止")

    def _on_message(self, data) -> None:
        try:
            self.logger.info(f"收到消息: {data}")

            sender = data.sender
            message = data.message
            if not message:
                return

            user_open_id = sender.open_id if sender else None
            chat_id = message.chat_id
            message_id = message.message_id

            content_str = message.content or ""
            try:
                content_obj = json.loads(content_str) if isinstance(content_str, str) else content_str
                text = content_obj.get("text", "") if isinstance(content_obj, dict) else str(content_obj)
            except (json.JSONDecodeError, TypeError):
                text = str(content_str)

            if self._is_allowed(user_open_id, chat_id):
                response = self.message_handler(text, user_open_id)
                self._send_reply(message_id, response)
            else:
                self.logger.info(f"用户 {user_open_id} 不在白名单中")

        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")

    def _is_allowed(self, user_open_id: str | None, chat_id: str | None) -> bool:
        if self.config.dm_policy == "open":
            return True
        if user_open_id and user_open_id in self.config.allow_from:
            return True
        if chat_id and chat_id in self.config.group_allow_from:
            return True
        return False

    def _send_reply(self, message_id: str, text: str) -> None:
        try:
            token = self.feishu_gateway.get_tenant_access_token()
            url = f"https://open.{self.config.domain}.cn/open-apis/im/v1/messages/{message_id}/reply"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            self.logger.info(f"回复已发送: {message_id}")
        except Exception as e:
            self.logger.error(f"发送回复失败: {e}")
