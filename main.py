"""启动入口"""

import argparse
from pathlib import Path

import yaml

from coleague.agent import ColeagueAgent
from coleague.gateway import FeishuGateway
from coleague.skills import SkillLoader
from coleague.tui import TUIMode


def run_tui(agent: ColeagueAgent, agent_name: str) -> None:
    tui = TUIMode(
        process_message=agent.process_message,
        agent_name=agent_name,
    )
    tui.start()


def run_service(agent: ColeagueAgent, agent_name: str) -> None:
    print(f"{agent_name} 已启动 (服务模式)")


def main() -> None:
    parser = argparse.ArgumentParser(description="同事.agent")
    parser.add_argument("--tui", action="store_true", help="启动 TUI 模式")
    parser.add_argument("--service", action="store_true", help="启动服务模式")
    args = parser.parse_args()

    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    feishu = FeishuGateway(
        webhook_url=config["feishu"]["webhook_url"],
        secret=config["feishu"].get("secret"),
    )

    skills_dir = Path(__file__).parent / config["skills"]["dir"]
    skill_loader = SkillLoader(skills_dir)

    agent = ColeagueAgent(feishu_gateway=feishu, skill_loader=skill_loader)
    agent.initialize()

    agent_name = config["agent"]["name"]

    if args.tui or not config["feishu"]["webhook_url"]:
        run_tui(agent, agent_name)
    elif args.service:
        run_service(agent, agent_name)
    else:
        run_tui(agent, agent_name)


if __name__ == "__main__":
    main()
