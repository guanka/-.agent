import json
import logging
import os
import select
import subprocess
import time
from pathlib import Path
from typing import Any


class MCPClient:
    def __init__(self, mcp_dir: str | Path, timeout: int = 30):
        self.mcp_dir = Path(mcp_dir)
        self.timeout = timeout
        self.logger = logging.getLogger("coleague.mcp")

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        input_data = json.dumps(payload) + "\n"
        self.logger.debug(f"MCP 调用: {tool_name} {arguments}")

        proc = None
        stdout_line = b""
        try:
            proc = subprocess.Popen(
                ["node", "dist/index.js"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.mcp_dir,
            )
            proc.stdin.write(input_data.encode("utf-8"))
            proc.stdin.flush()
            proc.stdin.close()

            fd = proc.stdout.fileno()
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                ready = select.select([fd], [], [], 0.1)[0]
                if ready:
                    chunk = os.read(fd, 4096)
                    if not chunk:
                        break
                    stdout_line += chunk
                    if b"\n" in stdout_line:
                        stdout_line = stdout_line[:stdout_line.index(b"\n")]
                        break
        except FileNotFoundError:
            raise RuntimeError("node 未找到，请确认 Node.js 已安装")
        finally:
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    pass

        stdout_text = stdout_line.decode("utf-8").strip()
        if not stdout_text:
            stderr = b""
            if proc:
                try:
                    stderr = proc.stderr.read()
                except Exception:
                    pass
            raise RuntimeError(f"MCP 无输出: {stderr.decode('utf-8', errors='replace')[:200]}")

        try:
            response = json.loads(stdout_text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"MCP 响应解析失败: {e}\n原始输出: {stdout_text[:200]}")

        if "error" in response:
            err = response["error"]
            raise RuntimeError(f"MCP 错误 {err.get('code')}: {err.get('message')}")

        return response.get("result", {})

    def exec_ssh(
        self,
        station: str,
        target_type: str,
        target_ip: str,
        command: str,
    ) -> str:
        result = self.call_tool(
            "exec_ssh",
            {
                "station": station,
                "target_type": target_type,
                "target_ip": target_ip,
                "command": command,
            },
        )
        content = result.get("content", [])
        text = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
        is_error = result.get("isError", False)
        if is_error:
            self.logger.warning(f"SSH 命令返回错误: {text[:100]}")
        return text

    def scp_file(
        self,
        station: str,
        target_type: str,
        target_ip: str,
        remote_path: str,
        local_path: str,
    ) -> str:
        result = self.call_tool(
            "scp_file",
            {
                "station": station,
                "target_type": target_type,
                "target_ip": target_ip,
                "remote_path": remote_path,
                "local_path": local_path,
            },
        )
        content = result.get("content", [])
        text = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
        is_error = result.get("isError", False)
        if is_error:
            self.logger.warning(f"SCP 文件下载返回错误: {text[:100]}")
        return text

    def get_tool_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "exec_ssh",
                    "description": "通过SSH跳板机连接到工厂工站或设备并执行命令。工站使用密码认证，设备使用证书认证。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "station": {
                                "type": "string",
                                "enum": ["poincare", "galois_p2", "galois_m4", "shenzhou"],
                                "description": "工站名称：poincare(庞加莱), galois_p2(伽罗华P2), galois_m4(伽罗华M4), shenzhou(神州)",
                            },
                            "target_type": {
                                "type": "string",
                                "enum": ["workstation", "device"],
                                "description": "目标类型：workstation(工站主机) 或 device(设备，使用证书认证)",
                            },
                            "target_ip": {
                                "type": "string",
                                "description": "目标机器的 IP 地址",
                            },
                            "command": {
                                "type": "string",
                                "description": "要在目标机器上执行的 shell 命令",
                            },
                        },
                        "required": ["station", "target_type", "target_ip", "command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "scp_file",
                    "description": "通过SCP/SFTP下载远程主机上的文件到本地，支持工站与设备两种目标类型，并复用跳板链连接。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "station": {
                                "type": "string",
                                "enum": ["poincare", "galois_p2", "galois_m4", "shenzhou"],
                                "description": "工站名称：poincare(庞加莱), galois_p2(伽罗华P2), galois_m4(伽罗华M4), shenzhou(神州)",
                            },
                            "target_type": {
                                "type": "string",
                                "enum": ["workstation", "device"],
                                "description": "目标类型：workstation(工站主机) 或 device(设备，使用证书认证)",
                            },
                            "target_ip": {
                                "type": "string",
                                "description": "目标机器的 IP 地址",
                            },
                            "remote_path": {
                                "type": "string",
                                "description": "远程文件路径（在目标机器上）",
                            },
                            "local_path": {
                                "type": "string",
                                "description": "本地保存路径（自动创建父目录）",
                            },
                        },
                        "required": ["station", "target_type", "target_ip", "remote_path", "local_path"],
                    },
                },
            },
        ]
