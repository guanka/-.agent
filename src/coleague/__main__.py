import argparse
import logging
import signal
import sys
from pathlib import Path

import yaml

from coleague.agent import ColeagueAgent
from coleague.gateway import FeishuConfig, FeishuGateway
from coleague.llm import GLMClient
from coleague.log import setup_logging
from coleague.secrets import load_secret
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


def run_service(agent: ColeagueAgent, agent_name: str, feishu_config: FeishuConfig | None) -> None:
    logger = logging.getLogger("coleague")
    
    if not feishu_config:
        logger.error("飞书未配置，无法启动服务模式")
        return

    from coleague.gateway.feishu_ws import FeishuWSService

    ws_service = FeishuWSService(
        config=feishu_config,
        message_handler=agent.process_message,
        agent=agent,
    )

    def signal_handler(sig, frame):
        logger.info("收到退出信号")
        ws_service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    ws_service.start()
    logger.info(f"{agent_name} 服务已启动 (WebSocket 模式)")

    signal.pause()


def main() -> None:
    parser = argparse.ArgumentParser(description="同事.agent")
    parser.add_argument("--tui", action="store_true", help="启动 TUI 模式")
    parser.add_argument("--service", action="store_true", help="启动服务模式 (WebSocket)")
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

    feishu_config_dict = config.get("feishu", {})
    feishu_enabled = feishu_config_dict.get("enabled", False)
    feishu_config: FeishuConfig | None = None

    if feishu_enabled:
        app_secret_cfg = feishu_config_dict.get("appSecret", "")
        if isinstance(app_secret_cfg, dict):
            app_secret = load_secret(
                source=app_secret_cfg.get("source", "file"),
                provider=app_secret_cfg.get("provider", ""),
                id=app_secret_cfg.get("id", ""),
            )
        else:
            app_secret = str(app_secret_cfg)

        feishu_config = FeishuConfig(
            enabled=True,
            app_id=feishu_config_dict.get("appId", ""),
            app_secret=app_secret,
            domain=feishu_config_dict.get("domain", "feishu"),
            connection_mode=feishu_config_dict.get("connectionMode", "websocket"),
            require_mention=feishu_config_dict.get("requireMention", True),
            dm_policy=feishu_config_dict.get("dmPolicy", "open"),
            allow_from=feishu_config_dict.get("allowFrom", []),
            group_allow_from=feishu_config_dict.get("groupAllowFrom", []),
            group_policy=feishu_config_dict.get("groupPolicy", "open"),
            groups=feishu_config_dict.get("groups", {}),
        )
        feishu = FeishuGateway(feishu_config)
        logger.info(f"飞书配置已加载: {feishu_config.app_id}")
    else:
        feishu = None
        logger.info("飞书网关未启用")

    skills_dir = root / config["skills"]["dir"]
    skill_loader = SkillLoader(skills_dir)

    _LLM_BASE_URLS = {
        "glm": "https://open.bigmodel.cn/api/paas/v4",
        "minimax": "https://api.minimaxi.com/v1/text/chatcompletion_v2",
    }

    llm_client = None
    if "llm" in config and config["llm"].get("api_key"):
        provider = config["llm"].get("provider", "glm")
        model = config["llm"].get("model", "glm-4")
        base_url = config["llm"].get("base_url") or _LLM_BASE_URLS.get(provider, _LLM_BASE_URLS["glm"])
        llm_client = GLMClient(
            api_key=config["llm"]["api_key"],
            model=model,
            base_url=base_url,
        )
        logger.info(f"LLM 已启用: {provider}/{model}")
    else:
        logger.warning("LLM 未配置，使用模拟模式")

    mcp_client = None
    mcp_cfg = config.get("mcp", {})
    if mcp_cfg.get("enabled", False):
        from coleague.mcp import MCPClient
        mcp_path = root / mcp_cfg.get("factory_path", "mcp/factory-mcp")
        mcp_client = MCPClient(mcp_dir=mcp_path, timeout=mcp_cfg.get("timeout", 30))
        logger.info(f"MCP 已启用: {mcp_path}")

    knowledge_loader = None
    knowledge_cfg = config.get("knowledge", {})
    if knowledge_cfg.get("enabled", False):
        from coleague.knowledge import KnowledgeLoader
        knowledge_path = root / knowledge_cfg.get("dir", "knowledge")
        knowledge_loader = KnowledgeLoader(knowledge_dir=knowledge_path)
        logger.info(f"知识库已启用: {knowledge_path}")

    agent_name = config["agent"]["name"]

    agent = ColeagueAgent(
        feishu_gateway=feishu,
        skill_loader=skill_loader,
        llm_client=llm_client,
        agent_name=agent_name,
        mcp_client=mcp_client,
        knowledge_loader=knowledge_loader,
    )
    agent.initialize()
    logger.info(f"技能加载完成: {agent_name}")

    try:
        if args.service:
            run_service(agent, agent_name, feishu_config)
        elif args.tui:
            run_tui(agent, agent_name)
        else:
            if feishu_enabled:
                run_service(agent, agent_name, feishu_config)
            else:
                run_tui(agent, agent_name)
    finally:
        if mcp_client:
            mcp_client.close()
        logger.info("同事.agent 退出")


if __name__ == "__main__":
    main()
