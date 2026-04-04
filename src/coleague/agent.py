"""智能体核心"""

from typing import Any

from coleague.gateway import FeishuGateway
from coleague.llm import GLMClient
from coleague.llm.glm import Message
from coleague.skills import SkillData, SkillLoader


class ColeagueAgent:
    def __init__(
        self,
        feishu_gateway: FeishuGateway,
        skill_loader: SkillLoader,
        llm_client: GLMClient | None = None,
        agent_name: str = "同事",
    ):
        self.feishu = feishu_gateway
        self.skills = skill_loader
        self.llm = llm_client
        self.agent_name = agent_name
        self._skill_data: SkillData | None = None
        self._conversation_history: list[Message] = []

    def initialize(self) -> None:
        self._skill_data = self.skills.load_colleague_skill()

    def process_message(self, message: str, user_open_id: str | None = None) -> str:
        if self._skill_data is None:
            self.initialize()

        response = self._generate_response(message)
        if user_open_id:
            self.feishu.send_text(response, open_id=user_open_id)
        return response

    def _generate_response(self, message: str) -> str:
        if self._skill_data is None:
            return "未初始化"

        if self.llm is None:
            return f"[{self.agent_name}] 收到消息: {message}"

        self._conversation_history.append(Message(role="user", content=message))

        system_prompt = self._build_system_prompt()
        all_messages = [Message(role="system", content=system_prompt)] + self._conversation_history

        response = self.llm.chat(all_messages)
        self._conversation_history.append(Message(role="assistant", content=response))
        return response

    def _build_system_prompt(self) -> str:
        if self._skill_data is None:
            return f"你是{self.agent_name}。"

        return self._skill_data.system_prompt
