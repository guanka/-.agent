"""启动入口"""

import argparse
import logging
from pathlib import Path

import yaml

from coleague.agent import ColeagueAgent
from coleague.gateway import FeishuGateway
from coleague.llm import GLMClient
from coleague.log import setup_logging
from coleague.skills import SkillLoader
from coleague.tui import TUIMode


def find_project_root() -> Path:
    import coleague
    package_path = Path(coleague.__file__).parent
    current = package_path.parent
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / "config.yaml").exists():
            return current
        current = current.parent
    return Path.cwd()


def run_tui(agent: ColeagueAgent, agent_name: str) -> None:
    logger = logging.getLogger("coleague.tui")
    tui = TUIMode(
        process_message=agent.process_message,
        agent_name=agent_name,
    )
    logger.info("TUI 模式启动")
    tui.start()
    logger.info("TUI 模式退出")


def run_service(agent: ColeagueAgent, agent_name: str) -> None:
    logger = logging.getLogger("coleague")
    logger.info(f"{agent_name} 已启动 (服务模式)")


def main() -> None:
    parser = argparse.ArgumentParser(description="同事.agent")
    parser.add_argument("--tui", action="store_true", help="启动 TUI 模式")
    parser.add_argument("--service", action="store_true", help="启动服务模式")
    args = parser.parse_args()

    root = find_project_root()
    config_path = root / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    log_config = config.get("logging", {})
    log_file = log_config.get("file", "/var/log/coleague.log")
    logger = setup_logging(
        level=log_config.get("level", "INFO"),
        log_file=log_file,
    )
    logger.info("=" * 50)
    logger.info("同事.agent 启动")
    logger.info("=" * 50)

    feishu = FeishuGateway(
        webhook_url=config["feishu"]["webhook_url"],
        secret=config["feishu"].get("secret"),
    )

    skills_dir = root / config["skills"]["dir"]
    skill_loader = SkillLoader(skills_dir)

    llm_client = None
    if "llm" in config and config["llm"].get("api_key"):
        llm_client = GLMClient(
            api_key=config["llm"]["api_key"],
            model=config["llm"].get("model", "glm-4"),
        )
        logger.info(f"LLM 已启用: {config['llm'].get('model', 'glm-4')}")
    else:
        logger.warning("LLM 未配置，使用模拟模式")

    agent_name = config["agent"]["name"]

    agent = ColeagueAgent(
        feishu_gateway=feishu,
        skill_loader=skill_loader,
        llm_client=llm_client,
        agent_name=agent_name,
    )
    agent.initialize()
    logger.info(f"技能加载完成: {agent_name}")

    if args.tui or not config["feishu"]["webhook_url"]:
        run_tui(agent, agent_name)
    elif args.service:
        run_service(agent, agent_name)
    else:
        run_tui(agent, agent_name)

    logger.info("同事.agent 退出")


if __name__ == "__main__":
    main()
