"""Browser and URL navigation tools for web actions."""
import webbrowser
import urllib.parse
from typing import Optional
from pydantic import BaseModel, Field

from tools.base import BaseTool, ToolResult
from security.permissions import RiskLevel, AccessDeniedError


class OpenUrlArgs(BaseModel):
    url: str = Field(description="Web URL to open in browser (e.g. 'https://www.youtube.com' or 'https://google.com')")


class PlayYoutubeArgs(BaseModel):
    query: str = Field(description="Search query or song/video title to play on YouTube (e.g. 'emraan hashmi songs')")


class SearchWebArgs(BaseModel):
    query: str = Field(description="Search query to look up on Google (e.g. 'latest AI news')")


class OpenUrlTool(BaseTool):
    name = "open_url"
    description = "Safely opens a website URL in the user's web browser."
    args_schema = OpenUrlArgs
    risk_level = RiskLevel.SAFE

    def execute(self, url: str) -> ToolResult:
        try:
            url_str = url.strip()
            if not (url_str.startswith("http://") or url_str.startswith("https://")):
                url_str = f"https://{url_str}"

            webbrowser.open(url_str)
            return ToolResult(
                success=True,
                data={"url": url_str},
                message=f"Opened website in browser: {url_str}"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PlayYoutubeTool(BaseTool):
    name = "play_youtube"
    description = "Searches and plays a video, song, or artist on YouTube in the browser."
    args_schema = PlayYoutubeArgs
    risk_level = RiskLevel.SAFE

    def execute(self, query: str) -> ToolResult:
        try:
            encoded_query = urllib.parse.quote_plus(query.strip())
            youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}"

            webbrowser.open(youtube_url)
            return ToolResult(
                success=True,
                data={"query": query, "url": youtube_url},
                message=f"Opened YouTube search for '{query}' in browser."
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SearchWebTool(BaseTool):
    name = "search_web"
    description = "Searches the web via Google in the default browser."
    args_schema = SearchWebArgs
    risk_level = RiskLevel.SAFE

    def execute(self, query: str) -> ToolResult:
        try:
            encoded_query = urllib.parse.quote_plus(query.strip())
            search_url = f"https://www.google.com/search?q={encoded_query}"

            webbrowser.open(search_url)
            return ToolResult(
                success=True,
                data={"query": query, "url": search_url},
                message=f"Opened Google search for '{query}' in browser."
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
