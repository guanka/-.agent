# 安装部署指南

## 环境要求

- Python >= 3.10
- Node.js >= 18（仅 MCP 功能需要）

## 1. 主智能体

```bash
# 创建虚拟环境
python3 -m venv coleague
source coleague/bin/activate

# 安装依赖
cd coleague.agent
pip install -e .
```

## 2. 配置

复制并编辑配置文件：

```bash
cp config.yaml.example config.yaml   # 如有模板，否则直接编辑 config.yaml
```

### config.yaml 说明

```yaml
# 飞书网关
feishu:
  enabled: true
  appId: "你的飞书应用 App ID"
  appSecret: "你的飞书应用 App Secret"
  domain: "feishu"              # feishu 或 lark
  connectionMode: "websocket"
  requireMention: true          # 群聊中是否需要 @机器人
  dmPolicy: "open"              # 私聊策略
  allowFrom: []                 # 允许的用户 open_id 列表
  groupAllowFrom: []            # 允许的群聊/用户 open_id 列表

# LLM 配置（二选一）
llm:
  provider: "glm"               # glm 或 minimax
  api_key: "你的 API Key"
  model: "glm-4"                # glm: glm-4 / minimax: MiniMax-M2.7
  # base_url: ""                # 可选，自定义 API 地址

# MCP 工厂跳板机（可选）
mcp:
  enabled: false
  factory_path: "mcp/factory_mcp"
  timeout: 120

# 设备知识库（可选）
knowledge:
  enabled: false
  dir: "knowledge"

# 智能体
agent:
  name: "陈皮"

# 日志
logging:
  level: "INFO"
  file: "./logs/coleague.log"
```

## 3. Factory MCP（可选）

仅在需要 SSH 跳板机功能时配置：

```bash
cd mcp/factory_mcp

# 安装依赖并编译
npm install
npx tsc

# 配置
cp config.json.example config.json
# 编辑 config.json，填入工站密码
```

如需设备证书认证，将证书放到 `mcp/factory_mcp/cert/device_login.pem` 并设置权限：

```bash
chmod 600 cert/device_login.pem
```

### 支持的工站

| 工站 | 标识 | 跳板机 |
|------|------|--------|
| 庞加莱 | `poincare` | 10.48.40.11 |
| 伽罗华P2 | `galois_p2` | 10.48.41.11 |
| 伽罗华P4 | `galois_p4` | 10.53.40.11 |
| 伽罗华M4 | `galois_m4` | 10.53.40.11 |
| 神州 | `shenzhou` | 43.145.26.102 (二跳) |

## 4. 运行

```bash
source coleague/bin/activate
cd coleague.agent

# 飞书 WebSocket 服务模式
python -m coleague --service

# 本地 TUI 调试模式
python -m coleague --tui

# 自动选择（有飞书配置则服务模式，否则 TUI）
python -m coleague
```

## 5. 常见问题

**飞书连接断开**：SDK 内置自动重连（`auto_reconnect=True`），消息处理已异步化不会阻塞心跳，正常情况下会自动恢复。

**LLM 不可用**：MiniMax 过载或网络异常时会自动重试（最多 3 次退避），仍失败则回复用户"当前 LLM 不可用"，不影响服务运行。

**飞书发送失败**：Token 过期时会自动刷新重试一次。
