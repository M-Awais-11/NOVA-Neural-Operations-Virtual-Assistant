"""SQLite-based conversation and execution memory manager."""
import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from config.settings import settings


class AgentMemory:
    """Manages persistent SQLite memory for commands, plans, and tool executions."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes database tables."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    plan TEXT,
                    tool_name TEXT,
                    tool_args TEXT,
                    tool_result TEXT,
                    agent_response TEXT,
                    status TEXT NOT NULL
                )
            """)
            conn.commit()

    @staticmethod
    def sanitize(text: Optional[str]) -> Optional[str]:
        """Redacts potential API keys and passwords from persisted memory."""
        if not text:
            return text
        # Redact common key patterns (e.g. sk-..., bearer tokens)
        text = re.sub(r'sk-[a-zA-Z0-9_-]{20,}', '[REDACTED_API_KEY]', text)
        text = re.sub(r'(password|passwd|secret|api_key|token)\s*[:=]\s*["\']?[^"\'\s]+["\']?', r'\1: [REDACTED]', text, flags=re.IGNORECASE)
        return text

    def log_interaction(
        self,
        user_input: str,
        plan: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        agent_response: Optional[str] = None,
        status: str = "SUCCESS"
    ) -> int:
        """Saves an agent execution step to the database."""
        timestamp = datetime.now().isoformat()
        sanitized_input = self.sanitize(user_input)
        sanitized_plan = self.sanitize(plan)
        sanitized_args = self.sanitize(json.dumps(tool_args)) if tool_args else None
        sanitized_result = self.sanitize(json.dumps(tool_result)) if tool_result else None
        sanitized_response = self.sanitize(agent_response)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO interactions (
                    timestamp, user_input, plan, tool_name, tool_args, tool_result, agent_response, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    sanitized_input,
                    sanitized_plan,
                    tool_name,
                    sanitized_args,
                    sanitized_result,
                    sanitized_response,
                    status
                )
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves the most recent interactions."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, timestamp, user_input, tool_name, agent_response, status
                FROM interactions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


# Global memory singleton
memory = AgentMemory()
