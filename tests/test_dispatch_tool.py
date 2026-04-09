import json
from unittest.mock import MagicMock

import pytest

from coleague.agent import ColeagueAgent


@pytest.fixture
def agent():
    skill_loader = MagicMock()
    mcp = MagicMock()
    a = ColeagueAgent(
        feishu_gateway=None,
        skill_loader=skill_loader,
        mcp_client=mcp,
    )
    return a


def _make_tool_call(name: str, arguments: dict, call_id: str = "1") -> dict:
    return {"id": call_id, "function": {"name": name, "arguments": json.dumps(arguments)}}


class TestDispatchTool:
    def test_exec_ssh_success(self, agent):
        agent.mcp.exec_ssh.return_value = "ok"
        tc = _make_tool_call("exec_ssh", {
            "station": "s1", "target_type": "host",
            "target_ip": "1.2.3.4", "command": "ls",
        })
        assert agent._dispatch_tool(tc) == "ok"
        agent.mcp.exec_ssh.assert_called_once_with(
            station="s1", target_type="host", target_ip="1.2.3.4", command="ls",
        )

    def test_exec_ssh_exception(self, agent):
        agent.mcp.exec_ssh.side_effect = RuntimeError("连接失败")
        tc = _make_tool_call("exec_ssh", {
            "station": "s1", "target_type": "host",
            "target_ip": "1.2.3.4", "command": "ls",
        })
        assert agent._dispatch_tool(tc) == "[SSH错误] 连接失败"

    def test_scp_file_success(self, agent):
        agent.mcp.scp_file.return_value = "copied"
        tc = _make_tool_call("scp_file", {
            "station": "s1", "target_type": "host",
            "target_ip": "1.2.3.4", "remote_path": "/tmp/a", "local_path": "/tmp/b",
        })
        assert agent._dispatch_tool(tc) == "copied"
        agent.mcp.scp_file.assert_called_once_with(
            station="s1", target_type="host", target_ip="1.2.3.4",
            remote_path="/tmp/a", local_path="/tmp/b",
        )

    def test_scp_file_exception(self, agent):
        agent.mcp.scp_file.side_effect = OSError("磁盘满")
        tc = _make_tool_call("scp_file", {
            "station": "s1", "target_type": "host",
            "target_ip": "1.2.3.4", "remote_path": "/tmp/a", "local_path": "/tmp/b",
        })
        assert agent._dispatch_tool(tc) == "[SCP错误] 磁盘满"

    def test_unknown_tool(self, agent):
        tc = _make_tool_call("no_such_tool", {"a": 1})
        assert agent._dispatch_tool(tc) == "[未知工具: no_such_tool]"

    def test_invalid_json_arguments(self, agent):
        tc = {"id": "1", "function": {"name": "exec_ssh", "arguments": "{bad json"}}
        assert agent._dispatch_tool(tc) == "[参数解析失败]"

    def test_empty_tool_call(self, agent):
        assert agent._dispatch_tool({}) == "[未知工具: ]"

    def test_no_mcp_client(self, agent):
        agent.mcp = None
        tc = _make_tool_call("exec_ssh", {
            "station": "s1", "target_type": "host",
            "target_ip": "1.2.3.4", "command": "ls",
        })
        assert agent._dispatch_tool(tc) == "[未知工具: exec_ssh]"

    def test_missing_function_field(self, agent):
        tc = {"id": "1"}
        assert agent._dispatch_tool(tc) == "[未知工具: ]"

    def test_missing_arguments_field(self, agent):
        """arguments 缺失时应默认解析为空 dict，exec_ssh 因缺参数抛 KeyError"""
        tc = {"id": "1", "function": {"name": "exec_ssh"}}
        result = agent._dispatch_tool(tc)
        assert "[SSH错误]" in result

    def test_exec_ssh_missing_required_arg(self, agent):
        tc = _make_tool_call("exec_ssh", {"station": "s1"})
        result = agent._dispatch_tool(tc)
        assert "[SSH错误]" in result

    def test_scp_file_missing_required_arg(self, agent):
        tc = _make_tool_call("scp_file", {"station": "s1"})
        result = agent._dispatch_tool(tc)
        assert "[SCP错误]" in result

    def test_real_case_pull_file_from_poincare_workstation(self, agent):
        """实际场景：去庞加莱的 10.248.67.110 工站，拉取 /root/poincare_discover.sh 文件"""
        agent.mcp.scp_file.return_value = "文件拉取成功: /root/poincare_discover.sh"
        tc = _make_tool_call("scp_file", {
            "station": "poincare",
            "target_type": "workstation",
            "target_ip": "10.248.67.110",
            "remote_path": "/root/poincare_discover.sh",
            "local_path": "/tmp/poincare_discover.sh",
        })
        result = agent._dispatch_tool(tc)
        assert result == "文件拉取成功: /root/poincare_discover.sh"
        agent.mcp.scp_file.assert_called_once_with(
            station="poincare",
            target_type="workstation",
            target_ip="10.248.67.110",
            remote_path="/root/poincare_discover.sh",
            local_path="/tmp/poincare_discover.sh",
        )
