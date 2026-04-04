# 同事.agent

基于飞书网关的智能体项目。

## 项目结构

```
coleague.agent/
├── config.yaml              # 配置文件
├── pyproject.toml           # 项目配置
├── src/coleague/
│   ├── __main__.py          # 启动入口
│   ├── agent.py             # 智能体核心
│   ├── gateway/
│   │   └── feishu.py        # 飞书网关
│   ├── llm/
│   │   └── glm.py           # 智谱 AI (GLM) 客户端
│   ├── log.py               # 日志模块
│   ├── skills/
│   │   └── loader.py        # 技能加载器
│   └── tui/
│       └── app.py           # TUI 交互界面
├── chenpi.skill/            # 技能数据目录
└── logs/                    # 日志目录 (自动创建)
```

## 安装

```bash
cd coleague.agent
pip install -e .
```

## 配置

编辑 `config.yaml`：

```yaml
feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL"
  secret: ""

llm:
  provider: "glm"
  api_key: "YOUR_API_KEY"
  model: "glm-4"

skills:
  dir: "."          # 指向包含 .skill 目录的位置

agent:
  name: "陈皮"

logging:
  level: "INFO"      # DEBUG, INFO, WARNING, ERROR
  dir: "./logs"      # 日志目录
```

## 运行

### TUI 模式 (默认，用于本地调试)

```bash
python -m coleague
```

### 服务模式

```bash
python -m coleague --service
```

## 日志

日志同时输出到控制台和文件 `logs/coleague.log`：

```
2026-04-04 22:49:29 [INFO] coleague: 同事.agent 启动
2026-04-04 22:49:29 [INFO] coleague.agent.陈皮: 技能加载完成: 陈皮
2026-04-04 22:49:29 [INFO] coleague: LLM 已启用: glm-4.7
```

查看日志：

```bash
tail -f logs/coleague.log
```

## 技能数据

技能数据来自 `{name}.skill/` 目录（如 `chenpi.skill/`），包含：

- `meta.json` - 元数据
- `SKILL.md` - 系统提示词和 persona
- `knowledge/` - 知识文档
