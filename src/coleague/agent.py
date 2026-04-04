"""智能体核心"""

from typing import Any

from coleague.gateway import FeishuGateway
from coleague.skills import SkillLoader


class ColeagueAgent:
    def __init__(
        self,
        feishu_gateway: FeishuGateway,
        skill_loader: SkillLoader,
    ):
        self.feishu = feishu_gateway
        self.skills = skill_loader
        self._colleague_data: dict[str, Any] | None = None

    def initialize(self) -> None:
        self._colleague_data = self.skills.load_colleague_skill()

    def process_message(self, message: str, user_open_id: str | None = None) -> str:
        if self._colleague_data is None:
            self.initialize()

        response = self._generate_response(message)
        self.feishu.send_text(response, open_id=user_open_id)
        return response

    def _generate_response(self, message: str) -> str:
        if self._colleague_data is None:
            return "未初始化"

        colleague_name = self._colleague_data.get("name", "未知同事")
        return f"[{colleague_name}] 收到消息: {message}"
