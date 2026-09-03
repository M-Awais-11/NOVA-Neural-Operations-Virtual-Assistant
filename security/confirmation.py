"""Interactive confirmation subsystem for risky and impactful actions."""
import sys

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from rich.console import Console
    from rich.panel import Panel
    console = Console(legacy_windows=False)
    HAS_RICH = True
except Exception:
    console = None
    HAS_RICH = False

from security.permissions import RiskLevel, ActionCancelledError
from config.settings import settings


class ConfirmationManager:
    """Handles prompting the user for approval before performing risky operations."""

    def __init__(self, auto_confirm: bool = False):
        self.auto_confirm = auto_confirm
        self.confirm_callback = None

    def confirm(self, action_name: str, details: str, risk_level: RiskLevel = RiskLevel.RISKY) -> bool:
        """
        Prompts user for yes/no confirmation when required.
        Raises ActionCancelledError if denied.
        """
        if self.auto_confirm or not settings.require_confirmation_for_risky_tools:
            return True

        if risk_level in (RiskLevel.SAFE, RiskLevel.MODERATE):
            return True

        # If a custom callback is registered (e.g. Tkinter GUI popup)
        if self.confirm_callback is not None:
            approved = self.confirm_callback(action_name, details, risk_level)
            if approved:
                return True
            else:
                raise ActionCancelledError(f"Action '{action_name}' was cancelled by the user.")


        if HAS_RICH and console:
            try:
                console.print(
                    Panel(
                        f"[bold yellow][!] CONFIRMATION REQUIRED[/bold yellow]\n\n"
                        f"[bold]Action:[/bold] {action_name}\n"
                        f"[bold]Target / Details:[/bold] {details}\n"
                        f"[bold]Risk Level:[/bold] [{ 'red' if risk_level == RiskLevel.RISKY else 'yellow' }]{risk_level.value}[/]\n\n"
                        f"Do you want to continue?",
                        title="[bold red]Security Guard[/bold red]",
                        border_style="yellow",
                    )
                )
            except Exception:
                print("\n" + "=" * 45)
                print("[!] CONFIRMATION REQUIRED")
                print(f"Action: {action_name}")
                print(f"Target / Details: {details}")
                print(f"Risk Level: {risk_level.value}")
                print("=" * 45)
        else:
            print("\n" + "=" * 45)
            print("[!] CONFIRMATION REQUIRED")
            print(f"Action: {action_name}")
            print(f"Target / Details: {details}")
            print(f"Risk Level: {risk_level.value}")
            print("=" * 45)

        try:
            response = input("Confirm execution? (yes/no): ").strip().lower()
            if response in ("y", "yes"):
                return True
            else:
                raise ActionCancelledError(f"Action '{action_name}' was cancelled by the user.")
        except (KeyboardInterrupt, EOFError):
            raise ActionCancelledError(f"Action '{action_name}' was aborted.")


confirmation_manager = ConfirmationManager()
