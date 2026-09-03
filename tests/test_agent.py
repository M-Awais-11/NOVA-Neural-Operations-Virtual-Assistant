"""Unit tests for agent planner, executor, verifier, and memory."""
import pytest
from pathlib import Path
from agent.verifier import Verifier
from agent.executor import Executor
from agent.planner import Planner, PlanResult, PlannedToolCall
from agent.agent import Agent
from memory.memory import AgentMemory
from tools.base import ToolResult
from tools.registry import ToolRegistry
from security.confirmation import ConfirmationManager
from security.path_validator import path_validator


@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    sandbox = tmp_path / "agent_env"
    sandbox.mkdir()
    monkeypatch.setattr(path_validator, "allowed_roots", [sandbox.resolve()])
    return sandbox


def test_verifier_create_folder(temp_env):
    folder = temp_env / "test_dir"
    folder.mkdir()

    v_res = Verifier.verify(
        tool_name="create_folder",
        tool_args={"path": str(folder)},
        result=ToolResult(success=True, data={"path": str(folder)})
    )
    assert v_res.verified is True


def test_verifier_create_file(temp_env):
    file_path = temp_env / "sample.txt"
    file_path.write_text("content")

    v_res = Verifier.verify(
        tool_name="create_file",
        tool_args={"path": str(file_path)},
        result=ToolResult(success=True, data={"path": str(file_path)})
    )
    assert v_res.verified is True


def test_executor_with_auto_confirm(temp_env):
    confirm_mgr = ConfirmationManager(auto_confirm=True)
    exec_inst = Executor(confirmation_mgr=confirm_mgr)

    target_file = temp_env / "exec_test.txt"
    step_res = exec_inst.execute_tool(
        "create_file",
        {"path": str(target_file), "content": "executor test"}
    )
    assert step_res.success is True
    assert step_res.verification.verified is True
    assert target_file.exists()


def test_memory_secret_redaction(tmp_path):
    db_file = tmp_path / "test_memory.db"
    mem = AgentMemory(db_path=db_file)

    secret_input = "My api key is sk-1234567890abcdef12345678 and password='MySecretPassword123!'"
    row_id = mem.log_interaction(
        user_input=secret_input,
        status="SUCCESS"
    )
    assert row_id > 0

    history = mem.get_recent_history(1)
    assert len(history) == 1
    assert "sk-1234567890" not in history[0]["user_input"]
    assert "[REDACTED" in history[0]["user_input"]


def test_agent_end_to_end_mock_planner(temp_env):
    class MockPlanner:
        model = "mock-model"
        def plan(self, user_input, history=None):
            target_path = str(temp_env / "mock_file.txt")
            return PlanResult(
                tool_calls=[
                    PlannedToolCall(
                        id="call_1",
                        tool_name="create_file",
                        arguments={"path": target_path, "content": "mock text"}
                    )
                ],
                direct_response="I will create the file."
            )

        def _call_llm_api(self, messages, tools=None):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "File mock_file.txt created successfully."
                        }
                    }
                ]
            }

    confirm_mgr = ConfirmationManager(auto_confirm=True)
    mock_executor = Executor(confirmation_mgr=confirm_mgr)
    test_agent = Agent(
        planner_instance=MockPlanner(),
        executor_instance=mock_executor,
        memory_instance=AgentMemory(db_path=temp_env / "mem.db")
    )

    response = test_agent.run("Create a file called mock_file.txt")
    assert response.success is True
    assert len(response.execution_results) == 1
    assert (temp_env / "mock_file.txt").exists()
