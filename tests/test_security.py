"""Unit tests for the security, sandboxing, and path validator modules."""
import pytest
from pathlib import Path
from security.path_validator import PathValidator, path_validator
from security.permissions import AccessDeniedError, RiskLevel, ActionCancelledError
from security.confirmation import ConfirmationManager


@pytest.fixture
def temp_sandbox(tmp_path):
    """Creates an isolated allowed sandbox directory for testing."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    return sandbox


def test_path_validator_allowed_directory(temp_sandbox):
    validator = PathValidator(allowed_roots=[temp_sandbox])
    valid_file = temp_sandbox / "sample.txt"
    resolved = validator.validate(valid_file)
    assert resolved == valid_file.resolve()


def test_path_validator_blocks_outside_directory(temp_sandbox, tmp_path):
    validator = PathValidator(allowed_roots=[temp_sandbox])
    outside_file = tmp_path / "outside.txt"
    outside_file.touch()

    with pytest.raises(AccessDeniedError) as exc:
        validator.validate(outside_file)
    assert "outside allowed directories" in str(exc.value).lower()


def test_path_validator_blocks_windows_system_dir(temp_sandbox):
    validator = PathValidator(allowed_roots=[temp_sandbox])
    system_path = Path(r"C:\Windows\System32\drivers\etc\hosts")

    with pytest.raises(AccessDeniedError) as exc:
        validator.validate(system_path)
    assert "access denied" in str(exc.value).lower()


def test_path_validator_blocks_sensitive_files(temp_sandbox):
    validator = PathValidator(allowed_roots=[temp_sandbox])
    env_file = temp_sandbox / ".env"
    ssh_key = temp_sandbox / "id_rsa"
    private_key = temp_sandbox / "server.key"

    for sensitive in (env_file, ssh_key, private_key):
        with pytest.raises(AccessDeniedError) as exc:
            validator.validate(sensitive)
        assert "sensitive" in str(exc.value).lower()


def test_path_validator_blocks_traversal_attempts(temp_sandbox):
    validator = PathValidator(allowed_roots=[temp_sandbox])
    traversal_path = temp_sandbox / ".." / ".." / "Windows" / "win.ini"

    with pytest.raises(AccessDeniedError):
        validator.validate(traversal_path)


def test_confirmation_manager_auto_confirm():
    mgr = ConfirmationManager(auto_confirm=True)
    assert mgr.confirm("test_action", "details", RiskLevel.RISKY) is True


def test_confirmation_manager_safe_action_no_prompt():
    mgr = ConfirmationManager(auto_confirm=False)
    assert mgr.confirm("read_file", "test.txt", RiskLevel.SAFE) is True
    assert mgr.confirm("create_file", "test.txt", RiskLevel.MODERATE) is True
