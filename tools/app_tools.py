"""Application launching tool with strict allowlist and process execution safety."""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from tools.base import BaseTool, ToolResult
from security.permissions import RiskLevel, AccessDeniedError
from security.path_validator import path_validator
from config.settings import settings


class OpenApplicationArgs(BaseModel):
    app_name: str = Field(description="Name of the allowlisted application to open (e.g. 'notepad', 'calc', 'paint', 'explorer', 'chrome', 'edge')")
    target_file: Optional[str] = Field(default=None, description="Optional safe file path or URL to open with the application")


class OpenApplicationTool(BaseTool):
    name = "open_application"
    description = "Safely opens an allowlisted Windows application (e.g. notepad, calc, paint, explorer, chrome, edge)."
    args_schema = OpenApplicationArgs
    risk_level = RiskLevel.RISKY

    def _resolve_executable(self, app_key: str) -> Optional[str]:
        """Finds executable path for the requested application."""
        allowed_apps = settings.allowed_applications
        if app_key not in allowed_apps:
            return None

        default_exe = allowed_apps[app_key]

        # Check if already in PATH
        which_path = shutil.which(default_exe)
        if which_path:
            return which_path

        # Windows known install locations for Chrome & Edge
        if app_key in ("chrome", "google chrome"):
            candidates = [
                Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
            ]
            for c in candidates:
                if c.exists():
                    return str(c)

        if app_key in ("edge", "msedge", "microsoft edge"):
            candidates = [
                Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
                Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Microsoft/Edge/Application/msedge.exe",
            ]
            for c in candidates:
                if c.exists():
                    return str(c)

        return default_exe

    def execute(self, app_name: str, target_file: Optional[str] = None) -> ToolResult:
        try:
            app_key = app_name.strip().lower()
            allowed_apps = settings.allowed_applications

            if app_key not in allowed_apps:
                allowed_list = ", ".join(sorted(set(allowed_apps.keys())))
                raise AccessDeniedError(
                    f"Application '{app_name}' is not in the allowed applications list. "
                    f"Allowed applications: {allowed_list}"
                )

            executable = self._resolve_executable(app_key)
            if not executable:
                raise FileNotFoundError(f"Could not locate executable for '{app_name}'.")

            cmd = [executable]

            if target_file:
                # If target is a URL or file
                if target_file.startswith("http://") or target_file.startswith("https://"):
                    cmd.append(target_file)
                else:
                    validated_target = path_validator.validate(target_file, must_exist=True)
                    cmd.append(str(validated_target))

            # Launch process safely in background without shell=True
            process = subprocess.Popen(
                cmd,
                shell=False,
                creationflags=subprocess.DETACHED_PROCESS if hasattr(subprocess, "DETACHED_PROCESS") else 0
            )

            return ToolResult(
                success=True,
                data={"app": app_key, "pid": process.pid, "target": target_file},
                message=f"Application '{app_key}' launched successfully (PID: {process.pid})."
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
