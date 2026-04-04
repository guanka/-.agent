"""启动入口"""

from pathlib import Path

import yaml

from coleague.agent import ColeagueAgent
from coleague.gateway import FeishuGateway
from coleague.skills import SkillLoader


def main() -> None:
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

    print(f"同事.agent 已启动: {config['agent']['name']}")


if __name__ == "__main__":
    main()
