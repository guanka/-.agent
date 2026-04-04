"""智能体核心"""

from typing import Any

from coleague.gateway import FeishuGateway
from coleague.llm import GLMClient
from coleague.llm.glm import Message
from coleague.skills import SkillLoader


class ColeagueAgent:
    def __init__(
        self,
        feishu_gateway: FeishuGateway,
        skill_loader: SkillLoader,
        llm_client: GLMClient | None = None,
    ):
        self.feishu = feishu_gateway
        self.skills = skill_loader
        self.llm = llm_client
        self._colleague_data: dict[str, Any] | None = None
        self._conversation_history: list[Message] = []

    def initialize(self) -> None:
        self._colleague_data = self.skills.load_colleague_skill()

    def process_message(self, message: str, user_open_id: str | None = None) -> str:
        if self._colleague_data is None:
            self.initialize()

        response = self._generate_response(message)
        if user_open_id:
            self.feishu.send_text(response, open_id=user_open_id)
        return response

    def _generate_response(self, message: str) -> str:
        if self._colleague_data is None:
            return "未初始化"

        if self.llm is None:
            colleague_name = self._colleague_data.get("name", "未知同事")
            return f"[{colleague_name}] 收到消息: {message}"

        self._conversation_history.append(Message(role="user", content=message))

        system_prompt = self._build_system_prompt()
        all_messages = [Message(role="system", content=system_prompt)] + self._conversation_history

        response = self.llm.chat(all_messages)
        self._conversation_history.append(Message(role="assistant", content=response))
        return response

    def _build_system_prompt(self) -> str:
        if self._colleague_data is None:
            return "你是一个智能助手。"

        name = self._colleague_data.get("name", "未知")
        role = self._colleague_data.get("role", "")
        skills = self._colleague_data.get("skills", [])

        prompt = f"你是{name}，{role}。" if role else f"你是{name}。"
        if skills:
            prompt += f" 你的技能包括：{', '.join(skills)}。"
        return prompt
