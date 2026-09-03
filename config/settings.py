"""Configuration module for the Local AI Desktop Agent with OpenRouter and OpenAI support."""
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


def get_active_windows_shell_folders() -> Dict[str, Path]:
    """
    Detects the true active Windows User Shell folders (including OneDrive redirected Desktop & Documents).
    """
    home = Path.home().resolve()
    folders = {
        "desktop": (home / "Desktop").resolve(),
        "documents": (home / "Documents").resolve(),
        "downloads": (home / "Downloads").resolve(),
    }

    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            )
            try:
                raw_desktop = winreg.QueryValueEx(key, "Desktop")[0]
                folders["desktop"] = Path(os.path.expandvars(raw_desktop)).resolve()
            except Exception:
                pass

            try:
                raw_docs = winreg.QueryValueEx(key, "Personal")[0]
                folders["documents"] = Path(os.path.expandvars(raw_docs)).resolve()
            except Exception:
                pass

            try:
                raw_downloads = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
                folders["downloads"] = Path(os.path.expandvars(raw_downloads)).resolve()
            except Exception:
                pass
            winreg.CloseKey(key)
        except Exception:
            pass

    # Secondary check: if OneDrive Desktop exists, ensure it's prioritized if active
    onedrive_desktop = (home / "OneDrive" / "Desktop").resolve()
    if onedrive_desktop.exists() and not folders["desktop"].exists():
        folders["desktop"] = onedrive_desktop

    return folders


class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # OpenRouter / OpenAI API Settings
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openai/gpt-4o-mini", alias="OPENROUTER_MODEL")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")

    # Optional direct OpenAI fallback
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: Optional[str] = Field(default=None, alias="OPENAI_MODEL")
    openai_base_url: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")

    # Security Sandboxing
    ai_workspace_dir: Optional[str] = Field(default=None, alias="AI_WORKSPACE_DIR")
    require_confirmation_for_risky_tools: bool = Field(default=True, alias="REQUIRE_CONFIRMATION")
    
    # Tool Execution Limits
    max_file_size_bytes: int = 5 * 1024 * 1024  # 5 MB
    search_max_results: int = 50
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # SQLite Memory Path
    db_path: Path = Field(
        default_factory=lambda: Path.home() / ".local_ai_agent" / "agent_memory.db"
    )

    @property
    def active_api_key(self) -> Optional[str]:
        """Returns the configured API key (OpenRouter priority, then OpenAI)."""
        return self.openrouter_api_key or self.openai_api_key

    @property
    def active_model(self) -> str:
        """Returns active model name."""
        if self.openrouter_api_key:
            return self.openrouter_model
        return self.openai_model or self.openrouter_model

    @property
    def active_base_url(self) -> str:
        """Returns the API endpoint URL."""
        if self.openai_base_url:
            return self.openai_base_url
        if self.openai_api_key and not self.openrouter_api_key:
            return "https://api.openai.com/v1"
        return self.openrouter_base_url

    @property
    def shell_folders(self) -> Dict[str, Path]:
        """Returns the detected shell folders dictionary."""
        return get_active_windows_shell_folders()

    @property
    def allowed_root_directories(self) -> List[Path]:
        """Returns the list of resolved directories the agent is permitted to read/write."""
        home = Path.home().resolve()
        shell_dirs = self.shell_folders
        
        roots: List[Path] = []
        
        # Add detected active shell folders
        for folder in shell_dirs.values():
            if folder.exists() and folder not in roots:
                roots.append(folder)

        # Also permit standard home Desktop/Documents/Downloads
        for standard in [(home / "Desktop").resolve(), (home / "Documents").resolve(), (home / "Downloads").resolve()]:
            if standard.exists() and standard not in roots:
                roots.append(standard)

        # Dedicated workspace directory
        if self.ai_workspace_dir:
            workspace = Path(self.ai_workspace_dir).expanduser().resolve()
        else:
            workspace = (home / "AI_Agent_Workspace").resolve()
            
        if workspace not in roots:
            roots.append(workspace)
        
        try:
            workspace.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        cwd = Path.cwd().resolve()
        if cwd not in roots:
            roots.append(cwd)

        # Add any local non-system drives (D:, E:, F:, etc.) that exist
        if sys.platform == "win32":
            import string
            system_drive = os.environ.get("SystemDrive", "C:").upper()[0]
            for drive_letter in string.ascii_uppercase:
                if drive_letter == system_drive:
                    continue  # Skip C: (system drive)
                drive_root = Path(f"{drive_letter}:\\").resolve()
                try:
                    if drive_root.exists() and drive_root not in roots:
                        roots.append(drive_root)
                except (OSError, PermissionError):
                    pass

        return roots


    @property
    def allowed_applications(self) -> Dict[str, str]:
        """Allowlisted applications map: name -> executable / command."""
        return {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "explorer": "explorer.exe",
            "this pc": "explorer.exe",
            "thispc": "explorer.exe",
            "my computer": "explorer.exe",
            "file explorer": "explorer.exe",
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "edge": "msedge.exe",
            "msedge": "msedge.exe",
            "microsoft edge": "msedge.exe",
        }


settings = Settings()
