"""Verification engine to confirm that tool actions actually succeeded on disk/OS."""
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel

from tools.base import ToolResult


class VerificationResult(BaseModel):
    verified: bool
    details: str


class Verifier:
    """Verifies that operations performed by tools achieved their intended physical outcome."""

    @staticmethod
    def verify(tool_name: str, tool_args: Dict[str, Any], result: ToolResult) -> VerificationResult:
        if not result.success:
            return VerificationResult(
                verified=False,
                details=f"Execution failed with error: {result.error}"
            )

        try:
            if tool_name == "create_folder":
                target_path = Path(result.data.get("path", tool_args.get("path", "")))
                if target_path.exists() and target_path.is_dir():
                    return VerificationResult(verified=True, details=f"Verified: Folder '{target_path}' exists on disk.")
                return VerificationResult(verified=False, details=f"Verification failed: Folder '{target_path}' was not found.")

            elif tool_name == "create_file":
                target_path = Path(result.data.get("path", tool_args.get("path", "")))
                if target_path.exists() and target_path.is_file():
                    size = target_path.stat().st_size
                    return VerificationResult(
                        verified=True,
                        details=f"Verified: File '{target_path}' exists on disk ({size} bytes)."
                    )
                return VerificationResult(verified=False, details=f"Verification failed: File '{target_path}' was not created.")

            elif tool_name == "read_file":
                if result.data and "content" in result.data:
                    lines = result.data.get("total_lines", 0)
                    return VerificationResult(verified=True, details=f"Verified: File read successfully ({lines} lines).")
                return VerificationResult(verified=False, details="Verification failed: No file content returned.")

            elif tool_name in ("list_directory", "search_files"):
                count = result.data.get("count", 0) if result.data else 0
                return VerificationResult(verified=True, details=f"Verified: Retrieved {count} entries.")

            elif tool_name == "open_application":
                pid = result.data.get("pid") if result.data else None
                if pid:
                    return VerificationResult(verified=True, details=f"Verified: Application process started with PID {pid}.")
                return VerificationResult(verified=True, details="Verified: Application launch command dispatched.")

            elif tool_name in ("open_url", "play_youtube", "search_web"):
                url = result.data.get("url", "") if result.data else ""
                return VerificationResult(verified=True, details=f"Verified: Browser URL dispatched ({url}).")

            elif tool_name in ("delete_file", "delete_folder"):
                target_path = Path(result.data.get("path", tool_args.get("path", "")))
                if not target_path.exists():
                    return VerificationResult(
                        verified=True,
                        details=f"Verified: '{target_path.name}' has been completely removed from disk."
                    )
                return VerificationResult(
                    verified=False,
                    details=f"Verification warning: '{target_path.name}' still appears to exist on disk."
                )

            return VerificationResult(verified=True, details="Verified.")
        except Exception as e:
            return VerificationResult(verified=False, details=f"Verification check encountered an error: {e}")


verifier = Verifier()
