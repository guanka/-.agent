import json
import logging
import os
import select
import subprocess
import time
from pathlib import Path
from typing import Any


class MCPClient:
    def __init__(self, mcp_dir: str | Path, timeout: int = 120):
        self.mcp_dir = Path(mcp_dir)
        self.timeout = timeout
        self.logger = logging.getLogger("coleague.mcp")
        self._proc: subprocess.Popen | None = None
        self._req_id = 0
        self._initialized = False

    def _ensure_started(self) -> subprocess.Popen:
        if self._proc and self._proc.poll() is None:
            return self._proc

        self.logger.info("启动 MCP 子进程")
        self._proc = subprocess.Popen(
            ["node", "dist/index.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.mcp_dir,
            env={**os.environ},
        )
        self._initialized = False
        self._do_initialize()
        return self._proc

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _send_and_recv(self, payload: dict) -> dict:
        proc = self._ensure_started()
        data = json.dumps(payload) + "\n"
        proc.stdin.write(data.encode("utf-8"))
        proc.stdin.flush()

        fd = proc.stdout.fileno()
        buf = b""
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            ready, _, _ = select.select([fd], [], [], 1.0)
            if ready:
                chunk = os.read(fd, 4096)
                if not chunk:
                    raise RuntimeError("MCP 子进程已退出")
                buf += chunk
                if b"\n" in buf:
                    line = buf[: buf.index(b"\n")].decode("utf-8").strip()
                    if line:
                        return json.loads(line)
        raise RuntimeError(f"MCP 调用超时 ({self.timeout}s)")

    def _do_initialize(self) -> None:
        resp = self._send_and_recv({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "coleague-agent", "version": "0.1.0"},
            },
        })
        self.logger.info(f"MCP 初始化完成: {resp.get('result', {}).get('serverInfo', {})}")

        # 发送 initialized 通知（无 id，无需等待响应）
        proc = self._proc
        notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        proc.stdin.write(notif.encode("utf-8"))
        proc.stdin.flush()
        self._initialized = True

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.logger.debug(f"MCP 调用: {tool_name} {arguments}")
        resp = self._send_and_recv({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        })
        if "error" in resp:
            err = resp["error"]
            raise RuntimeError(f"MCP 错误 {err.get('code')}: {err.get('message')}")
        return resp.get("result", {})

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self.logger.info("MCP 子进程已关闭")
        self._proc = None
        self._initialized = False

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
