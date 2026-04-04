"""TUI 主循环"""

import sys
from typing import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory


class TUIMode:
    def __init__(
        self,
        process_message: Callable[[str], str],
        agent_name: str = "智能体",
    ):
        self.process_message = process_message
        self.agent_name = agent_name
        self.running = False

    def start(self) -> None:
        self.running = True
        session = PromptSession(history=InMemoryHistory())

        print(f"[{self.agent_name}] TUI 模式启动 (输入 quit 退出)")
        print("-" * 40)

        while self.running:
            try:
                user_input = session.prompt("> ")
            except KeyboardInterrupt:
                print("\n再见!")
                break

            if not user_input.strip():
                continue

            if user_input.lower() in ("quit", "exit", "退出", "q"):
                print("再见!")
                self.running = False
                break

            response = self.process_message(user_input)
            print(f"[{self.agent_name}] {response}")

    def stop(self) -> None:
        self.running = False
