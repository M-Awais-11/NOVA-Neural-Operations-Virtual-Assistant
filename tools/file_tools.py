"""File and folder manipulation tools with strict security validation."""
import os
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from tools.base import BaseTool, ToolResult
from security.permissions import RiskLevel, AccessDeniedError
from security.path_validator import path_validator
from config.settings import settings


# --- Argument Schemas ---

class CreateFolderArgs(BaseModel):
    path: str = Field(description="Target directory path (e.g. 'Desktop/AI Projects' or 'AI_Agent_Workspace/reports')")


class CreateFileArgs(BaseModel):
    path: str = Field(description="Target file path (e.g. 'Desktop/AI Projects/notes.txt')")
    content: str = Field(default="", description="Text content to write into the file")
    overwrite: bool = Field(default=False, description="Whether to overwrite if file already exists")


class ReadFileArgs(BaseModel):
    path: str = Field(description="Path of the file to read (e.g. 'Desktop/AI Projects/notes.txt')")
    max_lines: Optional[int] = Field(default=500, description="Maximum number of lines to read")


class ListDirectoryArgs(BaseModel):
    path: Optional[str] = Field(default="Desktop", description="Directory path to list. Defaults to 'Desktop' or 'AI_Agent_Workspace'")


class SearchFilesArgs(BaseModel):
    query: str = Field(description="Filename search query or pattern (e.g. '*.txt', 'report', 'Django')")
    path: Optional[str] = Field(default=None, description="Root directory to search within (e.g. 'Documents' or 'Desktop')")
    extension: Optional[str] = Field(default=None, description="Optional extension filter (e.g. '.pdf', '.txt')")


# --- Tool Implementations ---

class CreateFolderTool(BaseTool):
    name = "create_folder"
    description = "Safely creates a new directory in an allowlisted location (Desktop, Documents, Downloads, or Workspace)."
    args_schema = CreateFolderArgs
    risk_level = RiskLevel.MODERATE

    def execute(self, path: str) -> ToolResult:
        try:
            target_path = path_validator.validate(path, must_exist=False)
            if target_path.exists() and not target_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"A file already exists at '{target_path}'. Cannot create folder."
                )

            target_path.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                success=True,
                data={"path": str(target_path)},
                message=f"Folder created successfully at: {target_path}"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CreateFileTool(BaseTool):
    name = "create_file"
    description = "Safely creates or writes a text file in an allowlisted location."
    args_schema = CreateFileArgs
    risk_level = RiskLevel.MODERATE

    def execute(self, path: str, content: str = "", overwrite: bool = False) -> ToolResult:
        try:
            target_path = path_validator.validate(path, must_exist=False)
            
            if target_path.exists() and not overwrite:
                return ToolResult(
                    success=False,
                    error=f"File already exists at '{target_path}'. Set overwrite=true if you want to replace it."
                )

            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            target_path.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                data={"path": str(target_path), "bytes_written": len(content.encode('utf-8'))},
                message=f"File created successfully at: {target_path}"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Safely reads content from a text or PDF file within allowed directories."
    args_schema = ReadFileArgs
    risk_level = RiskLevel.SAFE

    @staticmethod
    def _extract_pdf_text(target_path) -> str:
        """Extracts clean text from a PDF file using pypdf."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(target_path))
            pages_text = []
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    pages_text.append(f"--- Page {i} ---\n{text.strip()}")
            return "\n\n".join(pages_text) if pages_text else "[No extractable text found in PDF]"
        except ImportError:
            return "[ERROR: pypdf not installed. Run: pip install pypdf]"
        except Exception as e:
            return f"[PDF Read Error: {e}]"

    def execute(self, path: str, max_lines: Optional[int] = 500) -> ToolResult:
        try:
            target_path = path_validator.validate(path, must_exist=True, is_directory=False)

            file_size = target_path.stat().st_size
            if file_size > settings.max_file_size_bytes:
                return ToolResult(
                    success=False,
                    error=f"File is too large ({file_size} bytes). Limit is {settings.max_file_size_bytes} bytes."
                )

            # PDF files: use pypdf for proper text extraction
            if target_path.suffix.lower() == ".pdf":
                content = self._extract_pdf_text(target_path)
                lines = content.splitlines()
                total_lines = len(lines)
                if max_lines and total_lines > max_lines:
                    lines = lines[:max_lines]
                    content = "\n".join(lines) + f"\n\n[... Truncated: Showing {max_lines} of {total_lines} lines ...]"
                return ToolResult(
                    success=True,
                    data={
                        "path": str(target_path),
                        "total_lines": total_lines,
                        "content": content,
                        "file_type": "pdf"
                    },
                    message=f"Read {len(lines)} lines from PDF: {target_path.name}"
                )

            # Plain text / other files
            try:
                content = target_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                content = target_path.read_text(encoding="latin-1", errors="replace")

            lines = content.splitlines()
            total_lines = len(lines)
            if max_lines and total_lines > max_lines:
                lines = lines[:max_lines]
                content = "\n".join(lines) + f"\n\n[... Truncated: Showing {max_lines} of {total_lines} lines ...]"

            return ToolResult(
                success=True,
                data={
                    "path": str(target_path),
                    "total_lines": total_lines,
                    "content": content,
                    "file_type": "text"
                },
                message=f"Read {len(lines)} lines from {target_path.name}"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))



class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "Lists files and subdirectories inside an allowed directory with sizes and types."
    args_schema = ListDirectoryArgs
    risk_level = RiskLevel.SAFE

    def execute(self, path: Optional[str] = "Desktop") -> ToolResult:
        try:
            target_path = path_validator.validate(path or "Desktop", must_exist=True, is_directory=True)

            items: List[Dict[str, Any]] = []
            for entry in target_path.iterdir():
                # Skip hidden/sensitive entries
                if entry.name.startswith(".") or entry.name in (".env", ".git"):
                    continue

                try:
                    stat = entry.stat()
                    is_dir = entry.is_dir()
                    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    items.append({
                        "name": entry.name,
                        "type": "directory" if is_dir else "file",
                        "size_bytes": None if is_dir else stat.st_size,
                        "modified": mtime
                    })
                except Exception:
                    continue

            # Sort directories first, then alphabetically
            items.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))

            return ToolResult(
                success=True,
                data={"directory": str(target_path), "count": len(items), "items": items},
                message=f"Found {len(items)} items in {target_path}"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Searches for files matching a pattern or extension inside allowed directories."
    args_schema = SearchFilesArgs
    risk_level = RiskLevel.SAFE

    def execute(self, query: str, path: Optional[str] = None, extension: Optional[str] = None) -> ToolResult:
        try:
            root_path = path_validator.validate(path or "Desktop", must_exist=True, is_directory=True)

            query_lower = query.lower()
            ext_clean = ("." + extension.lstrip(".")).lower() if extension else None

            matches: List[Dict[str, Any]] = []
            for root, dirs, files in os.walk(root_path):
                # Prune sensitive subdirectories
                dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("windows", "appdata", "system32")]

                for file in files:
                    if file.startswith(".") or file in (".env", "id_rsa"):
                        continue

                    file_path = Path(root) / file
                    file_lower = file.lower()

                    # Extension match check
                    if ext_clean and not file_lower.endswith(ext_clean):
                        continue

                    # Query match check (either glob-like or substring)
                    if query_lower in file_lower or Path(file).match(query):
                        try:
                            stat = file_path.stat()
                            matches.append({
                                "name": file,
                                "path": str(file_path),
                                "size_bytes": stat.st_size,
                                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                            })
                        except Exception:
                            continue

                        if len(matches) >= settings.search_max_results:
                            break
                if len(matches) >= settings.search_max_results:
                    break

            return ToolResult(
                success=True,
                data={"query": query, "root": str(root_path), "count": len(matches), "matches": matches},
                message=f"Found {len(matches)} files matching '{query}' in {root_path}"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# --- Delete Argument Schemas ---

class DeleteFileArgs(BaseModel):
    path: str = Field(description="Path of the file to delete (e.g. 'Desktop/notes.txt' or 'E:/New Folder/test.txt')")


class DeleteFolderArgs(BaseModel):
    path: str = Field(description="Path of the folder to delete (e.g. 'Desktop/New Folder' or 'E:/New Folder')")
    force: bool = Field(default=False, description="If True, delete folder even if it contains files (recursive delete)")


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = (
        "Permanently deletes a file from an allowed directory. "
        "Requires user confirmation before executing."
    )
    args_schema = DeleteFileArgs
    risk_level = RiskLevel.RISKY

    def execute(self, path: str) -> ToolResult:
        try:
            import shutil
            target_path = path_validator.validate(path, must_exist=True, is_directory=False)
            file_name = target_path.name
            file_size = target_path.stat().st_size

            import stat
            try:
                os.chmod(target_path, stat.S_IWRITE)
            except Exception:
                pass

            target_path.unlink()

            return ToolResult(
                success=True,
                data={"path": str(target_path), "file_name": file_name, "size_bytes": file_size},
                message=f"File '{file_name}' deleted successfully from {target_path.parent}"
            )
        except FileNotFoundError:
            return ToolResult(success=False, error=f"File not found: '{path}'")
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: Cannot delete '{path}'")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DeleteFolderTool(BaseTool):
    name = "delete_folder"
    description = (
        "Permanently deletes a folder and optionally all its contents from an allowed directory. "
        "Requires user confirmation before executing."
    )
    args_schema = DeleteFolderArgs
    risk_level = RiskLevel.RISKY

    def execute(self, path: str, force: bool = False) -> ToolResult:
        try:
            import shutil
            import stat
            target_path = path_validator.validate(path, must_exist=True, is_directory=True)
            folder_name = target_path.name

            # Count contents before deleting
            contents = list(target_path.iterdir())
            item_count = len(contents)

            if item_count > 0 and not force:
                return ToolResult(
                    success=False,
                    error=(
                        f"Folder '{folder_name}' is not empty ({item_count} items inside). "
                        "Use force=True to delete it along with all its contents."
                    )
                )

            # Error handler for Windows read-only files/folders
            def _handle_remove_readonly(func, file_path, exc_info):
                try:
                    os.chmod(file_path, stat.S_IWRITE)
                    func(file_path)
                except Exception:
                    pass

            # Clear read-only on folder itself
            try:
                os.chmod(target_path, stat.S_IWRITE)
            except Exception:
                pass

            shutil.rmtree(str(target_path), onexc=_handle_remove_readonly)

            # Double check if completely removed; if not, try once more
            if target_path.exists():
                try:
                    os.chmod(target_path, stat.S_IWRITE)
                    target_path.rmdir()
                except Exception:
                    pass

            return ToolResult(
                success=True,
                data={"path": str(target_path), "folder_name": folder_name, "items_deleted": item_count},
                message=f"Folder '{folder_name}' and {item_count} item(s) inside deleted successfully."
            )
        except FileNotFoundError:
            return ToolResult(success=False, error=f"Folder not found: '{path}'")
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: Cannot delete folder '{path}'")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

