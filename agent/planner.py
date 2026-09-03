"""Planner module for translating natural language into structured tool calls via OpenRouter / OpenAI API."""
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from config.settings import settings
from tools.registry import tool_registry

logger = logging.getLogger(__name__)


class PlannedToolCall(BaseModel):
    id: str
    tool_name: str
    arguments: Dict[str, Any]


class PlanResult(BaseModel):
    tool_calls: List[PlannedToolCall] = []
    direct_response: Optional[str] = None
    raw_message: Optional[Dict[str, Any]] = None



def _build_system_prompt() -> str:
    """Builds a dynamic system prompt that reflects current allowed directories and tools."""
    from config.settings import settings
    roots = settings.allowed_root_directories
    roots_str = "\n".join(f"   - {r}" for r in roots)

    return f"""You are a Local AI Desktop Assistant for Windows.
Your job is to assist the user by understanding their natural-language commands and using the available safe tools.

Allowed directories (you CAN read, write, and delete inside these):
{roots_str}

Security Rules & Guidelines:
1. Available tools:
   - File & Folder: create_folder, create_file, read_file, list_directory, search_files
   - Delete: delete_file (delete a file), delete_folder (delete a folder, use force=True for non-empty folders)
   - Applications: open_application (for notepad, calculator, paint, explorer / this pc, chrome, edge)
   - Web & Media: open_url (open websites), play_youtube (play songs/videos on YouTube), search_web (search Google)
2. You CAN delete files and folders from ANY of the allowed directories above, including D:\\ and E:\\ drives.
3. When user says "go to E drive and delete X" or "delete folder X from E:" or "go to general(E)", use delete_folder with path='E:/X'.
4. Never invent or execute arbitrary shell commands.
5. If the user asks to play a song/video or go to YouTube, call 'play_youtube' with the query.
6. If the user asks to open This PC or File Explorer, call 'open_application' with app_name='explorer'.
7. If the user asks to open Chrome or Edge, call 'open_application' with app_name='chrome' or 'edge'.
8. If the user is greeting or asking a general question, respond directly without calling any tools.
9. For delete operations, always use the delete_file or delete_folder tool — NEVER refuse if the path is in the allowed directories list.
"""

# Export default system prompt for backward compatibility
SYSTEM_PROMPT = _build_system_prompt()




class Planner:
    """Plans tool calls from natural language user input using OpenRouter / OpenAI API."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self._custom_model = model
        self._custom_api_key = api_key
        self._custom_base_url = base_url

    @property
    def model(self) -> str:
        return self._custom_model or settings.active_model

    @property
    def api_key(self) -> Optional[str]:
        return self._custom_api_key or settings.active_api_key

    @property
    def base_url(self) -> str:
        url = self._custom_base_url or settings.active_base_url
        return url.rstrip("/")

    def _call_llm_api(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Makes an HTTP request to OpenRouter or OpenAI chat completions endpoint."""
        if not self.api_key:
            raise ValueError(
                "API Key is not configured! Please set OPENROUTER_API_KEY in your .env file."
            )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/local-ai-desktop-agent",
            "X-Title": "Local AI Desktop Agent",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            err_text = response.text
            try:
                err_json = response.json()
                err_text = err_json.get("error", {}).get("message", err_text)
            except Exception:
                pass
            raise RuntimeError(f"API Error (Status {response.status_code}): {err_text}")

        return response.json()

    def plan(self, user_input: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> PlanResult:
        """Sends user input and tool specifications to the LLM and returns the execution plan."""
        tools = tool_registry.get_openai_tools()

        messages: List[Dict[str, Any]] = [{"role": "system", "content": _build_system_prompt()}]

        # Append recent conversation history
        if conversation_history:
            for item in conversation_history[-6:]:
                messages.append(item)

        messages.append({"role": "user", "content": user_input})

        try:
            data = self._call_llm_api(messages=messages, tools=tools)
            choice = data["choices"][0]
            message = choice["message"]

            planned_calls: List[PlannedToolCall] = []

            tool_calls = message.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    fn_name = func.get("name", "")
                    raw_args = func.get("arguments", "{}")
                    if isinstance(raw_args, str):
                        try:
                            args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            args = {}
                    else:
                        args = raw_args

                    planned_calls.append(
                        PlannedToolCall(
                            id=tc.get("id", f"call_{fn_name}"),
                            tool_name=fn_name,
                            arguments=args
                        )
                    )

            return PlanResult(
                tool_calls=planned_calls,
                direct_response=message.get("content"),
                raw_message=message
            )

        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")
            raise e


planner = Planner()
