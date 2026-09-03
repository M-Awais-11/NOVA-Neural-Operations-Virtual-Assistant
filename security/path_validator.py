"""Path validation and sandboxing engine to prevent unauthorized system access."""
import os
from pathlib import Path
from typing import List, Optional
from config.settings import settings
from security.permissions import AccessDeniedError

# Blocked sensitive filenames / extensions / patterns
BLOCKED_PATTERNS = {
    ".env",
    ".ssh",
    ".aws",
    ".gnupg",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".pem",
    ".key",
    ".pfx",
    "sam",
    "system",
    "security",
    "ntuser.dat",
}


class PathValidator:
    """Validates and sanitizes file and folder paths against allowlists."""

    def __init__(self, allowed_roots: Optional[List[Path]] = None):
        self._custom_allowed_roots = allowed_roots

    @property
    def allowed_roots(self) -> List[Path]:
        return self._custom_allowed_roots if self._custom_allowed_roots is not None else settings.allowed_root_directories

    @allowed_roots.setter
    def allowed_roots(self, value: List[Path]):
        self._custom_allowed_roots = value

    def resolve_path(self, raw_path: str | Path) -> Path:
        """
        Resolves a user or LLM provided path string into a canonical absolute Path.
        Handles convenient aliases like 'Desktop/test' -> 'C:/Users/.../Desktop/test'.
        """
        if not raw_path:
            raise AccessDeniedError("Path cannot be empty.")

        path_str = str(raw_path).strip()

        # Handle common shortcuts using detected active Windows shell folders
        shell_dirs = settings.shell_folders
        home = Path.home()
        lower_path = path_str.lower().replace("\\", "/")

        if lower_path.startswith("desktop/") or lower_path == "desktop":
            base = shell_dirs.get("desktop", home / "Desktop")
            target = base / path_str[len("desktop/"):].lstrip("/\\")
        elif lower_path.startswith("documents/") or lower_path == "documents":
            base = shell_dirs.get("documents", home / "Documents")
            target = base / path_str[len("documents/"):].lstrip("/\\")
        elif lower_path.startswith("downloads/") or lower_path == "downloads":
            base = shell_dirs.get("downloads", home / "Downloads")
            target = base / path_str[len("downloads/"):].lstrip("/\\")
        elif lower_path.startswith("workspace/") or lower_path == "workspace":
            workspace = Path(settings.ai_workspace_dir).expanduser() if settings.ai_workspace_dir else (home / "AI_Agent_Workspace")
            target = workspace / path_str[len("workspace/"):].lstrip("/\\")
        else:
            # Check for Windows drive aliases like "General (E:)", "general(E)", "E drive", "drive E"
            import re
            drive_match = re.match(r"^(?:.*?\(([a-zA-Z]):?\)|([a-zA-Z])\s*drive|drive\s*([a-zA-Z]))[\\/]*(.*)$", path_str, re.IGNORECASE)
            if drive_match:
                letter = (drive_match.group(1) or drive_match.group(2) or drive_match.group(3)).upper()
                rest = drive_match.group(4)
                target = Path(f"{letter}:/") / rest
            else:
                expanded = os.path.expandvars(os.path.expanduser(path_str))
                p = Path(expanded)
                if not p.is_absolute():
                    workspace = Path(settings.ai_workspace_dir).expanduser() if settings.ai_workspace_dir else (home / "AI_Agent_Workspace")
                    target = (workspace / p)
                else:
                    target = p

        resolved_target = target.resolve()

        # Handle active Windows shell redirection (e.g. OneDrive Desktop & Documents)
        local_desktop = (home / "Desktop").resolve()
        active_desktop = shell_dirs.get("desktop", local_desktop).resolve()
        if active_desktop != local_desktop:
            try:
                rel = resolved_target.relative_to(local_desktop)
                resolved_target = (active_desktop / rel).resolve()
            except ValueError:
                pass

        local_docs = (home / "Documents").resolve()
        active_docs = shell_dirs.get("documents", local_docs).resolve()
        if active_docs != local_docs:
            try:
                rel = resolved_target.relative_to(local_docs)
                resolved_target = (active_docs / rel).resolve()
            except ValueError:
                pass

        return resolved_target

    def validate(self, raw_path: str | Path, must_exist: bool = False, is_directory: Optional[bool] = None) -> Path:
        """
        Validates that the path is strictly within the allowed directories and does not target
        sensitive files or forbidden system directories.
        """
        resolved = self.resolve_path(raw_path)
        resolved_str = str(resolved).lower()

        # Check explicit system directory roots
        system_roots = [
            Path(os.environ.get("SystemRoot", "C:/Windows")).resolve(),
            Path(os.environ.get("ProgramFiles", "C:/Program Files")).resolve(),
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")).resolve(),
            Path(os.environ.get("ProgramData", "C:/ProgramData")).resolve(),
        ]
        for sys_root in system_roots:
            try:
                resolved.relative_to(sys_root)
                raise AccessDeniedError(
                    f"Access Denied: Access to system directory '{sys_root}' is strictly prohibited."
                )
            except ValueError:
                pass

        # Check for system substring patterns (e.g. system32, syswow64)
        for sub in ("system32", "syswow64"):
            if sub in resolved_str:
                raise AccessDeniedError(
                    f"Access Denied: Access to system directory containing '{sub}' is strictly prohibited."
                )

        # Check for sensitive files / extensions / name matches
        parts = [p.lower() for p in resolved.parts]
        for pattern in BLOCKED_PATTERNS:
            if pattern in parts or resolved.name.lower() == pattern or resolved.suffix.lower() == pattern:
                raise AccessDeniedError(
                    f"Access Denied: Access to sensitive file/folder '{resolved.name}' is prohibited."
                )

        # Ensure path is strictly a subpath of one of the allowed roots
        is_allowed = False
        for root in self.allowed_roots:
            try:
                resolved.relative_to(root)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            allowed_list_str = "\n  - " + "\n  - ".join(str(r) for r in self.allowed_roots)
            raise AccessDeniedError(
                f"Access Denied: Path '{resolved}' is outside allowed directories:{allowed_list_str}"
            )

        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: '{resolved}'")

        if is_directory is True and resolved.exists() and not resolved.is_dir():
            raise NotADirectoryError(f"Path is not a directory: '{resolved}'")

        if is_directory is False and resolved.exists() and not resolved.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: '{resolved}'")

        return resolved


# Global validator instance
path_validator = PathValidator()
