"""Base tool classes and result structures for tool execution."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field
from security.permissions import RiskLevel


class ToolResult(BaseModel):
    """Encapsulates the standard output of a tool execution."""
    success: bool
    data: Optional[Any] = None
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BaseTool(ABC):
    """Abstract base class for all agent tools."""
    name: str
    description: str
    args_schema: Type[BaseModel]
    risk_level: RiskLevel = RiskLevel.SAFE

    def get_openai_tool_schema(self) -> Dict[str, Any]:
        """Generates OpenAI function calling schema from Pydantic args_schema."""
        schema = self.args_schema.model_json_schema()
        # Clean up unwanted metadata from schema for OpenAI compliance
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Executes the tool with validated arguments."""
        pass
