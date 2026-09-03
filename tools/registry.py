"""Tool registry for registering, looking up, and exporting tool schemas."""
from typing import Dict, List, Optional
from tools.base import BaseTool
from tools.file_tools import (
    CreateFolderTool,
    CreateFileTool,
    ReadFileTool,
    ListDirectoryTool,
    SearchFilesTool,
    DeleteFileTool,
    DeleteFolderTool,
)
from tools.app_tools import OpenApplicationTool
from tools.browser_tools import OpenUrlTool, PlayYoutubeTool, SearchWebTool


class ToolRegistry:
    """Manages available tools and provides access for agent planner and executor."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        tools = [
            CreateFolderTool(),
            CreateFileTool(),
            ReadFileTool(),
            ListDirectoryTool(),
            SearchFilesTool(),
            DeleteFileTool(),
            DeleteFolderTool(),
            OpenApplicationTool(),
            OpenUrlTool(),
            PlayYoutubeTool(),
            SearchWebTool(),
        ]
        for tool in tools:
            self.register(tool)


    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieves a tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def get_openai_tools(self) -> List[Dict]:
        """Exports all tools in OpenAI function calling schema format."""
        return [tool.get_openai_tool_schema() for tool in self._tools.values()]


# Default singleton registry
tool_registry = ToolRegistry()
