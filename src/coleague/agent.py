import json
import logging
from typing import Any

from coleague.gateway import FeishuConfig, FeishuGateway
from coleague.llm import GLMClient
from coleague.llm.glm import Message
from coleague.skills import SkillData, SkillLoader


class ColeagueAgent:
    def __init__(
        self,
        feishu_gateway: FeishuGateway | None,
        skill_loader: SkillLoader,
        llm_client: GLMClient | None = None,
        agent_name: str = "同事",
        mcp_client: Any | None = None,
        knowledge_loader: Any | None = None,
    ):
        self.feishu = feishu_gateway
        self.skills = skill_loader
        self.llm = llm_client
        self.agent_name = agent_name
        self.mcp = mcp_client
        self.knowledge = knowledge_loader
        self._skill_data: SkillData | None = None
        self._knowledge_context: str = ""
        self._conversation_history: list[Message] = []
        self.logger = logging.getLogger(f"coleague.agent.{agent_name}")

    def initialize(self) -> None:
        self._skill_data = self.skills.load_colleague_skill()
        self.logger.info(f"技能加载完成: {self._skill_data.meta.get('name', 'unknown')}")

        if self.knowledge:
            self._knowledge_context = self.knowledge.build_system_context()
            if self._knowledge_context:
                self.logger.info("知识库加载完成")

    def process_message(self, message: str, user_open_id: str | None = None) -> str:
        if self._skill_data is None:
            self.initialize()

        self.logger.info(f"收到消息: {message[:100]}...")
        response = self._generate_response(message)
        self.logger.info(f"发送响应: {response[:100]}...")
        return response

    def _generate_response(self, message: str) -> str:
        if self._skill_data is None:
            return "未初始化"

        if self.llm is None:
            return f"[{self.agent_name}] 收到消息: {message}"

        self._conversation_history.append(Message(role="user", content=message))
        system_prompt = self._build_system_prompt()
        all_messages = [Message(role="system", content=system_prompt)] + self._conversation_history

        if self.mcp:
            return self._generate_with_tools(all_messages)

        response = self.llm.chat(all_messages)
        self._conversation_history.append(Message(role="assistant", content=response))
        return response

    def _generate_with_tools(self, messages: list[Message]) -> str:
        assert self.mcp is not None
        assert self.llm is not None
        tools = [self.mcp.get_tool_schema()]
        history = list(messages)

        for _ in range(10):
            raw = self.llm.chat_with_tools(history, tools)
            tool_calls = raw.get("tool_calls") or []

            if not tool_calls:
                content = raw.get("content", "")
                self._conversation_history.append(Message(role="assistant", content=content))
                return content

            assistant_msg = Message(
                role="assistant",
                content=raw.get("content") or "",
                tool_calls=tool_calls,
            )
            history.append(assistant_msg)
            self._conversation_history.append(assistant_msg)

            for tc in tool_calls:
                tool_result = self._dispatch_tool(tc)
                result_msg = Message(
                    role="tool",
                    content=tool_result,
                    tool_call_id=tc.get("id", ""),
                )
                history.append(result_msg)
                self._conversation_history.append(result_msg)

        return "工具调用次数超限"

    def _dispatch_tool(self, tool_call: dict) -> str:
        name = tool_call.get("function", {}).get("name", "")
        try:
            args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
        except json.JSONDecodeError:
            return "[参数解析失败]"

        self.logger.info(f"调用工具: {name} {args}")

        if name == "exec_ssh" and self.mcp:
            try:
                return self.mcp.exec_ssh(
                    station=args["station"],
                    target_type=args["target_type"],
                    target_ip=args["target_ip"],
                    command=args["command"],
                )
            except Exception as e:
                self.logger.error(f"exec_ssh 失败: {e}")
                return f"[SSH错误] {e}"

        return f"[未知工具: {name}]"

    def _build_system_prompt(self) -> str:
        if self._skill_data is None:
            return f"你是{self.agent_name}。"

        parts = [self._skill_data.system_prompt]
        if self._knowledge_context:
            parts.append(self._knowledge_context)
        return "\n\n".join(parts)
