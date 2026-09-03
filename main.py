"""Main CMD-style CLI entry point for the Local AI Desktop Agent."""
import sys
import os
import json
import platform
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        os.system("title AI DESKTOP AGENT - Windows Command Prompt")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
load_dotenv()

from config.settings import settings
from agent.agent import agent, AgentResponse
from memory.memory import memory


def get_current_prompt_path() -> str:
    """Returns the current path in standard Windows CMD format."""
    try:
        home_path = str(Path.home())
        return home_path
    except Exception:
        return r"C:\Users\User"


def print_cmd_banner():
    """Prints the authentic Windows CMD banner."""
    win_version = platform.version() or "10.0.22631"
    print(f"Microsoft Windows [Version {win_version}]")
    print("(c) Microsoft Corporation. All rights reserved.")
    print()
    print("[AI Desktop Agent Core - Type 'help' for instructions, 'cls' to clear, 'exit' to quit]")
    print()


def display_history():
    """Displays recent interactions from SQLite memory."""
    records = memory.get_recent_history(limit=10)
    if not records:
        print("[History] No past interactions recorded.")
        return

    print("\n--- RECENT COMMAND HISTORY ---")
    print(f"{'ID':<4} | {'TIMESTAMP':<19} | {'STATUS':<9} | {'TOOL':<16} | {'COMMAND'}")
    print("-" * 75)
    for rec in records:
        cmd_snippet = rec["user_input"][:30] + ("..." if len(rec["user_input"]) > 30 else "")
        tool_snippet = (rec["tool_name"] or "-")[:15]
        print(f"{rec['id']:<4} | {rec['timestamp'][:19]} | {rec['status']:<9} | {tool_snippet:<16} | {cmd_snippet}")
    print("-" * 75)
    print()


def display_help():
    """Displays CMD-style help guide."""
    print("""
===============================================================================
                     AI DESKTOP AGENT - HELP & EXAMPLES
===============================================================================
You can type natural language commands directly at the prompt:

* File & Folder:
  - Create a folder named MyProjects on my Desktop
  - Create a text file notes.txt inside Desktop/MyProjects with text "Hello World"
  - Read notes.txt from Desktop/MyProjects and summarize it
  - List all files on my Desktop
  - Search for .pdf files in Documents

* Applications & Web:
  - Open Notepad
  - Open This PC (or Open File Explorer)
  - Open Calculator
  - Open Chrome and play a song of Emraan Hashmi on YouTube
  - Search Google for latest AI Agent news

* Utility Commands:
  - history       : View SQLite command logs
  - cls / clear   : Clear the command prompt screen
  - help          : Show this help manual
  - exit / quit   : Exit the agent
===============================================================================
""")


def main():
    """Main CMD interaction loop."""
    print_cmd_banner()

    # Check API key
    if not settings.active_api_key:
        print("[WARNING] API Key is not configured in .env file!")
        print("Please configure OPENROUTER_API_KEY=sk-or-v1-... in your .env file.\n")

    current_dir = get_current_prompt_path()

    while True:
        try:
            prompt_str = f"{current_dir}> "
            user_input = input(prompt_str).strip()

            if not user_input:
                continue

            cmd_lower = user_input.lower()
            if cmd_lower in ("exit", "quit"):
                print("\nExiting AI Desktop Agent. Goodbye!\n")
                break
            elif cmd_lower in ("cls", "clear"):
                os.system("cls" if os.name == "nt" else "clear")
                print_cmd_banner()
                continue
            elif cmd_lower == "help":
                display_help()
                continue
            elif cmd_lower == "history":
                display_history()
                continue

            # Process command
            print("\n[AI Processing] Planning task...")
            response: AgentResponse = agent.run(user_input)

            # Display Planned Steps
            if response.plan_steps:
                print("\n[Execution Plan]")
                for i, step in enumerate(response.plan_steps, 1):
                    args_str = ", ".join(f"{k}='{v}'" for k, v in step["arguments"].items())
                    print(f"  {i}. {step['tool']}({args_str})")
                print()

            # Display Step Results
            for result in response.execution_results:
                if result.cancelled:
                    print(f"  [CANCELLED] {result.tool_name}: Cancelled by user.")
                elif result.success:
                    print(f"  [SUCCESS] {result.tool_name}: {result.tool_result.message}")
                    if result.verification.verified:
                        print(f"            {result.verification.details}")
                else:
                    print(f"  [FAILED] {result.tool_name}: {result.error}")

            # Display Final Answer
            print("\n[Agent Response]")
            print(response.final_response)
            print()

        except KeyboardInterrupt:
            print("\n\n^C (Command interrupted)\n")
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred: {e}\n")


if __name__ == "__main__":
    main()
