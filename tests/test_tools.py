"""Unit tests for tool system."""
import pytest
from pathlib import Path
from tools.file_tools import (
    CreateFolderTool,
    CreateFileTool,
    ReadFileTool,
    ListDirectoryTool,
    SearchFilesTool,
)
from tools.app_tools import OpenApplicationTool
from security.path_validator import path_validator


@pytest.fixture(autouse=True)
def setup_test_sandbox(tmp_path, monkeypatch):
    """Configures an isolated sandbox for file tools during testing."""
    sandbox = tmp_path / "agent_sandbox"
    sandbox.mkdir()
    monkeypatch.setattr(path_validator, "allowed_roots", [sandbox.resolve()])
    return sandbox


def test_create_folder_tool(setup_test_sandbox):
    tool = CreateFolderTool()
    folder_path = setup_test_sandbox / "subfolder"
    result = tool.execute(path=str(folder_path))

    assert result.success is True
    assert folder_path.exists()
    assert folder_path.is_dir()


def test_create_file_tool(setup_test_sandbox):
    tool = CreateFileTool()
    file_path = setup_test_sandbox / "notes.txt"
    content = "Hello Local AI Agent!"

    result = tool.execute(path=str(file_path), content=content)
    assert result.success is True
    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == content


def test_create_file_overwrite_protection(setup_test_sandbox):
    tool = CreateFileTool()
    file_path = setup_test_sandbox / "existing.txt"
    file_path.write_text("initial", encoding="utf-8")

    # Overwrite = False should fail
    result_fail = tool.execute(path=str(file_path), content="new", overwrite=False)
    assert result_fail.success is False
    assert "already exists" in result_fail.error

    # Overwrite = True should succeed
    result_ok = tool.execute(path=str(file_path), content="new content", overwrite=True)
    assert result_ok.success is True
    assert file_path.read_text(encoding="utf-8") == "new content"


def test_read_file_tool(setup_test_sandbox):
    tool = ReadFileTool()
    file_path = setup_test_sandbox / "doc.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

    result = tool.execute(path=str(file_path))
    assert result.success is True
    assert result.data["total_lines"] == 3
    assert "Line 1" in result.data["content"]


def test_list_directory_tool(setup_test_sandbox):
    # Setup test structure
    (setup_test_sandbox / "dir1").mkdir()
    (setup_test_sandbox / "file1.txt").write_text("test")

    tool = ListDirectoryTool()
    result = tool.execute(path=str(setup_test_sandbox))

    assert result.success is True
    assert result.data["count"] == 2
    names = [item["name"] for item in result.data["items"]]
    assert "dir1" in names
    assert "file1.txt" in names


def test_search_files_tool(setup_test_sandbox):
    (setup_test_sandbox / "data.csv").write_text("1,2,3")
    (setup_test_sandbox / "report.pdf").write_text("pdf header")
    (setup_test_sandbox / "nested").mkdir()
    (setup_test_sandbox / "nested" / "sub_data.csv").write_text("4,5,6")

    tool = SearchFilesTool()
    result = tool.execute(query="data", path=str(setup_test_sandbox))

    assert result.success is True
    assert result.data["count"] == 2


def test_open_application_blocks_unauthorized():
    tool = OpenApplicationTool()
    result = tool.execute(app_name="powershell.exe")
    assert result.success is False
    assert "not in the allowed applications" in result.error


def test_delete_file_tool(setup_test_sandbox):
    from tools.file_tools import DeleteFileTool
    test_file = setup_test_sandbox / "to_delete.txt"
    test_file.write_text("temporary content")
    assert test_file.exists()

    tool = DeleteFileTool()
    result = tool.execute(path=str(test_file))
    assert result.success is True
    assert not test_file.exists()


def test_delete_folder_tool(setup_test_sandbox):
    from tools.file_tools import DeleteFolderTool
    test_dir = setup_test_sandbox / "folder_to_delete"
    test_dir.mkdir()
    (test_dir / "inside.txt").write_text("hello")

    tool = DeleteFolderTool()
    # Should fail without force when directory is non-empty
    result = tool.execute(path=str(test_dir), force=False)
    assert result.success is False

    # Should succeed with force=True
    result_force = tool.execute(path=str(test_dir), force=True)
    assert result_force.success is True
    assert not test_dir.exists()

