# 同事.agent

基于飞书网关的智能体项目。

## 项目结构

```
coleague.agent/
├── config.yaml              # 配置文件
├── main.py                  # 启动入口
├── pyproject.toml           # 项目配置
├── src/coleague/
│   ├── agent.py             # 智能体核心
│   ├── gateway/
│   │   └── feishu.py        # 飞书网关
│   └── skills/
│       └── loader.py        # 技能加载器
└── skills/                  # 同事.skill 数据目录
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

skills:
  dir: "./skills"

agent:
  name: "同事"
```

## 运行

```bash
python main.py
```

## 技能数据

在 `skills/` 目录下放置 `同事.json`，格式示例：

```json
{
  "name": "张三",
  "role": "后端工程师",
  "skills": ["Python", "Go", "架构设计"]
}
```
