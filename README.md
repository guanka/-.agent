# 同事.agent

基于飞书网关的智能体项目，支持 WebSocket 长连接接收消息。

## 项目结构

```
coleague.agent/
├── config.yaml.example        # 配置文件模板
├── pyproject.toml            # 项目配置
├── src/coleague/
│   ├── __main__.py           # 启动入口
│   ├── agent.py              # 智能体核心
│   ├── gateway/
│   │   ├── feishu.py        # 飞书 API 客户端
│   │   └── feishu_ws.py      # 飞书 WebSocket 服务
│   ├── llm/
│   │   └── glm.py            # 智谱 AI (GLM) 客户端
│   ├── log.py                # 日志模块
│   ├── secrets.py            # 密钥读取模块
│   ├── skills/
│   │   └── loader.py         # 技能加载器
│   └── tui/
│       └── app.py            # TUI 交互界面
├── chenpi.skill/             # 技能数据目录
└── logs/                     # 日志目录 (自动创建)
```

## 安装

```bash
cd coleague.agent
pip install -e .
```

## 配置

复制配置文件模板并编辑：

```bash
cp config.yaml.example config.yaml
```

`config.yaml` 配置示例：

```yaml
feishu:
  enabled: true
  appId: "YOUR_APP_ID"
  appSecret: "YOUR_APP_SECRET"
  domain: "feishu"
  connectionMode: "websocket"
  requireMention: true
  dmPolicy: "open"
  allowFrom:
    - "ou_xxxxxxxx"
  groupAllowFrom:
    - "ou_xxxxxxxx"
    - "oc_xxxxxxxx"
  groupPolicy: "open"
  groups:
    "*":
      enabled: true

llm:
  provider: "glm"
  api_key: "YOUR_API_KEY"
  model: "glm-4"

skills:
  dir: "."          # 指向包含 .skill 目录的位置

agent:
  name: "王三"

logging:
  level: "INFO"
  file: "./logs/coleague.log"
```

## 运行

### TUI 模式 (本地调试)

```bash
python -m coleague
```

### 服务模式 (WebSocket，长连接)

```bash
python -m coleague --service
```

## 日志

日志输出到文件 `logs/coleague.log`：

```
2026-04-05 07:24:07 [INFO] coleague: 同事.agent 启动
2026-04-05 07:24:07 [INFO] coleague.feishu.ws: 飞书 WebSocket 服务已启动
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
