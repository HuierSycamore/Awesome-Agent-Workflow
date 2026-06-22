"""
Question Tracker 黑盒测试文件

通过 stdio 启动 MCP Server 子进程，发送 JSON-RPC 请求，验证完整响应。
不 import 任何 mcp_server 模块。
"""

import pytest
import os
import sys
import json
import subprocess
import tempfile
import shutil

STATE_FILE = ".question_state.json"


@pytest.fixture
def temp_dir():
    """创建临时目录作为工作目录"""
    tmp = tempfile.mkdtemp()
    orig = os.getcwd()
    os.chdir(tmp)
    yield tmp
    os.chdir(orig)
    shutil.rmtree(tmp)


@pytest.fixture
def clean_state(temp_dir):
    """确保测试前状态文件干净"""
    state_file = os.path.join(temp_dir, STATE_FILE)
    if os.path.exists(state_file):
        os.remove(state_file)
    yield
    if os.path.exists(state_file):
        os.remove(state_file)


class TestBlackBox:
    """BB01-BB05: 黑盒测试，通过 stdio 启动子进程"""

    @pytest.fixture
    def mcp_process(self, temp_dir):
        """启动 MCP Server 子进程"""
        server_path = os.path.join(os.path.dirname(__file__), "mcp_server.py")
        proc = subprocess.Popen(
            [sys.executable, server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            cwd=temp_dir
        )
        yield proc
        proc.terminate()
        proc.wait(timeout=5)

    def _initialize(self, proc):
        """初始化 MCP 连接"""
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test",
                    "version": "1.0.0"
                }
            },
            "id": 0
        }
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        return json.loads(response_line)

    def _call_tool(self, proc, tool_name, arguments, req_id=1):
        """调用 MCP 工具，返回解析后的结果数据"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": req_id
        }
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        response = json.loads(response_line)

        if "error" in response:
            return response

        result_text = response["result"]["content"][0]["text"]
        return json.loads(result_text)

    def test_bb01_complete_workflow(self, mcp_process, clean_state):
        """BB01: 完整澄清流程 - 每个响应符合 JSON-RPC 规范，finalize 返回 status=ready"""
        self._initialize(mcp_process)

        r1 = self._call_tool(mcp_process, "add_questions", {"questions": ["问题A", "问题B", "问题C"]})
        assert "added_count" in r1
        assert r1["added_count"] == 3

        r2 = self._call_tool(mcp_process, "answer_question", {"question": "问题A", "answer": "答案A"})
        assert "matched_question" in r2

        r3 = self._call_tool(mcp_process, "answer_question", {"question": "问题B", "answer": "答案B"})
        assert "matched_question" in r3

        r3b = self._call_tool(mcp_process, "answer_question", {"question": "问题C", "answer": "答案C"})
        assert "matched_question" in r3b

        r4 = self._call_tool(mcp_process, "finalize_questions", {})
        assert r4["status"] == "ready"
        assert len(r4["summary"]) == 3

    def test_bb02_error_response_format(self, mcp_process, clean_state):
        """BB02: 异常响应格式 - 响应符合 JSON-RPC 规范，result 中含 error 字段"""
        self._initialize(mcp_process)

        self._call_tool(mcp_process, "add_questions", {"questions": ["问题A"]})

        r = self._call_tool(mcp_process, "answer_question", {"question": "不存在的原文", "answer": "答案"})

        assert "error" in r
        assert "未匹配到问题" in r["error"]

    def test_bb03_persistence_recovery(self, mcp_process, clean_state, temp_dir):
        """BB03: 重启恢复 - 恢复后 pending=1，answered=1，问题原文完整保留"""
        self._initialize(mcp_process)

        self._call_tool(mcp_process, "add_questions", {"questions": ["问题A", "问题B"]})
        self._call_tool(mcp_process, "answer_question", {"question": "问题A", "answer": "答案A"})

        proc_id = mcp_process.pid
        mcp_process.terminate()
        mcp_process.wait(timeout=5)

        new_proc = subprocess.Popen(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mcp_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            cwd=temp_dir
        )

        try:
            self._initialize(new_proc)
            r = self._call_tool(new_proc, "get_status", {"detail": "full"})
            assert r["pending"] == 1
            assert r["answered"] == 1

            questions = r["questions"]
            questions_text = [q["question"] for q in questions]
            assert "问题A" in questions_text
            assert "问题B" in questions_text
        finally:
            new_proc.terminate()
            new_proc.wait(timeout=5)

    def test_bb04_external_clear_new_design(self, mcp_process, clean_state, temp_dir):
        """BB04: 外部清空后新设计 - total=1，next_id=2"""
        self._initialize(mcp_process)

        self._call_tool(mcp_process, "add_questions", {"questions": ["问题A", "问题B"]})
        self._call_tool(mcp_process, "answer_question", {"question": "问题A", "answer": "答案A"})

        mcp_process.terminate()
        mcp_process.wait(timeout=5)

        state_file = os.path.join(temp_dir, STATE_FILE)
        if os.path.exists(state_file):
            os.remove(state_file)

        new_proc = subprocess.Popen(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mcp_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            cwd=temp_dir
        )

        try:
            self._initialize(new_proc)
            self._call_tool(new_proc, "add_questions", {"questions": ["新问题"]})
            r = self._call_tool(new_proc, "get_status", {"detail": "full"})

            assert r["total"] == 1

            with open(os.path.join(temp_dir, STATE_FILE), "r", encoding="utf-8") as f:
                state = json.load(f)
            assert state["next_id"] == 2
        finally:
            new_proc.terminate()
            new_proc.wait(timeout=5)

    def test_bb05_jsonrpc_protocol_error(self, mcp_process, clean_state):
        """BB05: JSON-RPC 协议错误 - 服务器对非 JSON 输入不崩溃，返回有效 JSON"""
        self._initialize(mcp_process)

        mcp_process.stdin.write("这不是有效的JSON\n")
        mcp_process.stdin.flush()

        response_line = mcp_process.stdout.readline()
        response = json.loads(response_line)

        assert isinstance(response, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
