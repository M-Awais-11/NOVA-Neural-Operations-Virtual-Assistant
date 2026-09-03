"""Tkinter-based Animated Windows CMD Interface for Local AI Desktop Agent."""
import sys
import os
import time
import queue
import threading
import platform
import tkinter as tk
from tkinter import ttk, font
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

from config.settings import settings
from agent.agent import agent, AgentResponse
from memory.memory import memory


class AnimatedTerminalGUI:
    """Animated Windows CMD Desktop Terminal for AI Agent."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Command Prompt - NOVA-Neural-Operations-Virtual-Assistant ")
        self.root.geometry("920x620")
        self.root.minsize(700, 450)
        self.root.configure(bg="#0C0C0C")

        # Set taskbar icon / dark titlebar if on Windows 11/10
        if sys.platform == "win32":
            try:
                import ctypes
                # Enable dark mode for window title bar (DWMWA_USE_IMMERSIVE_DARK_MODE)
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                value = ctypes.c_int(1)
                set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
            except Exception:
                pass

        # Fonts
        self.mono_font = font.Font(family="Consolas", size=11)
        self.mono_font_bold = font.Font(family="Consolas", size=11, weight="bold")
        self.prompt_font = font.Font(family="Consolas", size=11, weight="bold")

        # History tracking
        self.history_list = []
        self.history_index = -1
        self.ui_queue = queue.Queue()
        self.is_processing = False

        # Current working prompt path
        try:
            self.current_path = str(Path.home())
        except Exception:
            self.current_path = r"C:\Users\muham"

        # Build UI layout
        self._build_ui()

        # Start animation loops & queue listener
        self._process_queue()
        self._start_blinking_cursor()

        # Startup sequence animation
        self.root.after(100, self._play_boot_animation)

    def _build_ui(self):
        """Constructs the CMD-style terminal interface."""
        # Top title bar indicator
        self.header_frame = tk.Frame(self.root, bg="#1E1E1E", height=28)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(
            self.header_frame,
            text=" 🖥️  Command Prompt - NOVA-Neural-Operations-Virtual-Assistant ",
            bg="#1E1E1E",
            fg="#CCCCCC",
            font=("Segoe UI", 9),
            anchor="w"
        )
        title_lbl.pack(side=tk.LEFT, padx=8, pady=3)

        status_lbl = tk.Label(
            self.header_frame,
            text="● ACTIVE | OpenRouter ",
            bg="#1E1E1E",
            fg="#00FF7F",
            font=("Segoe UI", 8, "bold"),
            anchor="e"
        )
        status_lbl.pack(side=tk.RIGHT, padx=10, pady=3)

        # Terminal text display area
        self.text_frame = tk.Frame(self.root, bg="#0C0C0C")
        self.text_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))

        self.scrollbar = tk.Scrollbar(self.text_frame, bg="#1E1E1E", troughcolor="#0C0C0C", width=12)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.terminal = tk.Text(
            self.text_frame,
            bg="#0C0C0C",
            fg="#CCCCCC",
            insertbackground="#FFFFFF",
            selectbackground="#264F78",
            font=self.mono_font,
            wrap=tk.WORD,
            yscrollcommand=self.scrollbar.set,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            state=tk.DISABLED,
            cursor="xterm"
        )
        self.terminal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.terminal.yview)

        # Configure style tags
        self.terminal.tag_config("cmd_header", foreground="#888888")
        self.terminal.tag_config("system_info", foreground="#00E5FF")
        self.terminal.tag_config("prompt_label", foreground="#00FF7F", font=self.mono_font_bold)
        self.terminal.tag_config("user_cmd", foreground="#FFFFFF", font=self.mono_font_bold)
        self.terminal.tag_config("plan_title", foreground="#FFD700", font=self.mono_font_bold)
        self.terminal.tag_config("plan_step", foreground="#FFEA70")
        self.terminal.tag_config("success", foreground="#00FF7F")
        self.terminal.tag_config("failed", foreground="#FF5252")
        self.terminal.tag_config("cancelled", foreground="#FFA726")
        self.terminal.tag_config("agent_response", foreground="#E0E0E0")
        self.terminal.tag_config("spinner", foreground="#00E5FF", font=self.mono_font_bold)

        # Bottom Input Prompt Bar
        self.input_frame = tk.Frame(self.root, bg="#0C0C0C", height=38)
        self.input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=10)

        self.prompt_label = tk.Label(
            self.input_frame,
            text=f"{self.current_path}>",
            bg="#0C0C0C",
            fg="#00FF7F",
            font=self.prompt_font,
            anchor="w"
        )
        self.prompt_label.pack(side=tk.LEFT, padx=(0, 6))

        self.cmd_entry = tk.Entry(
            self.input_frame,
            bg="#0C0C0C",
            fg="#FFFFFF",
            insertbackground="#00FF7F",
            font=self.mono_font,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#333333",
            highlightcolor="#00FF7F"
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self.cmd_entry.focus_set()

        # Keyboard bindings
        self.cmd_entry.bind("<Return>", self._on_enter_pressed)
        self.cmd_entry.bind("<Up>", self._on_history_up)
        self.cmd_entry.bind("<Down>", self._on_history_down)
        self.terminal.bind("<Button-1>", lambda e: self.cmd_entry.focus_set())

    def _append_text(self, text: str, tag: str = ""):
        """Appends text to the terminal output."""
        self.terminal.config(state=tk.NORMAL)
        if tag:
            self.terminal.insert(tk.END, text, tag)
        else:
            self.terminal.insert(tk.END, text)
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)

    def _play_boot_animation(self):
        """Simulates authentic CMD boot up sequence."""
        win_version = platform.version() or "10.0.26200"
        lines = [
            (f"Microsoft Windows [Version {win_version}]\n", "cmd_header"),
            ("(c) Microsoft Corporation. All rights reserved.\n\n", "cmd_header"),
            ("[AI Desktop Agent OS Core] Connected & Initialized.\n", "system_info"),
            ("Type your command in natural language, 'help', 'cls', or 'exit'.\n\n", "cmd_header")
        ]

        def animate_line(idx):
            if idx < len(lines):
                text, tag = lines[idx]
                self._append_text(text, tag)
                self.root.after(120, lambda: animate_line(idx + 1))

        animate_line(0)

    def _start_blinking_cursor(self):
        """Blinks the prompt cursor subtly when idle."""
        pass  # Tkinter native entry handles the caret, custom effects are rendered inline

    def _on_enter_pressed(self, event):
        """Handles command submission."""
        if self.is_processing:
            return

        command = self.cmd_entry.get().strip()
        self.cmd_entry.delete(0, tk.END)

        if not command:
            return

        # Add to history
        self.history_list.append(command)
        self.history_index = len(self.history_list)

        # Print user prompt on terminal
        self._append_text(f"{self.current_path}> ", "prompt_label")
        self._append_text(f"{command}\n", "user_cmd")

        cmd_lower = command.lower()

        # Handle local utility commands immediately
        if cmd_lower in ("cls", "clear"):
            self.terminal.config(state=tk.NORMAL)
            self.terminal.delete("1.0", tk.END)
            self.terminal.config(state=tk.DISABLED)
            self._play_boot_animation()
            return
        elif cmd_lower in ("exit", "quit"):
            self._append_text("\n[Session Terminated] Closing Agent...\n", "system_info")
            self.root.after(600, self.root.destroy)
            return
        elif cmd_lower == "help":
            self._show_help()
            return
        elif cmd_lower == "history":
            self._show_history()
            return

        # Execute in background thread
        self.is_processing = True
        self.cmd_entry.config(state=tk.DISABLED)
        threading.Thread(target=self._run_agent_thread, args=(command,), daemon=True).start()

    def _show_help(self):
        help_text = """
======================================================================
    NOVA-Neural-Operations-Virtual-Assistant  - HELP & EXAMPLES
======================================================================
Commands you can run:
• Create Folder: Create a folder named MyProjects on my Desktop
• Create File  : Create a text file notes.txt inside Desktop/MyProjects
• Read & Summarize: Read notes.txt from Desktop/MyProjects
• Web & Media  : Open chrome and play atif aslam on youtube
• Open Apps    : Open Notepad | Open Calculator | Open This PC
• Utilities    : cls (clear), history, help, exit
======================================================================\n
"""
        self._append_text(help_text, "cmd_header")

    def _show_history(self):
        records = memory.get_recent_history(limit=10)
        if not records:
            self._append_text("[History] No past records found.\n\n", "cmd_header")
            return

        self._append_text("\n--- RECENT COMMAND LOGS ---\n", "system_info")
        for r in records:
            status_tag = "success" if r["status"] == "SUCCESS" else "failed"
            self._append_text(f"[{r['timestamp'][:19]}] ", "cmd_header")
            self._append_text(f"{r['status']:<8} ", status_tag)
            self._append_text(f"{r['user_input']}\n", "agent_response")
        self._append_text("---------------------------\n\n", "system_info")

    def _run_agent_thread(self, user_input: str):
        """Worker thread that communicates with LLM and runs tools."""
        # Spinner animation in UI
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        stop_spinner = threading.Event()

        def animate_spinner():
            idx = 0
            while not stop_spinner.is_set():
                char = spinner_chars[idx % len(spinner_chars)]
                self.ui_queue.put(("SPINNER_UPDATE", f"\n[AI Processing {char}] Planning and executing..."))
                time.sleep(0.08)
                idx += 1

        spinner_thread = threading.Thread(target=animate_spinner, daemon=True)
        spinner_thread.start()

        try:
            # Run the agent
            response: AgentResponse = agent.run(user_input)
            stop_spinner.set()
            time.sleep(0.1)
            self.ui_queue.put(("AGENT_COMPLETE", response))
        except Exception as e:
            stop_spinner.set()
            time.sleep(0.1)
            self.ui_queue.put(("AGENT_ERROR", str(e)))

    def _process_queue(self):
        """Reads updates from worker threads and animates them in UI."""
        try:
            while True:
                msg_type, data = self.ui_queue.get_nowait()

                if msg_type == "AGENT_COMPLETE":
                    response: AgentResponse = data

                    # Print Execution Plan
                    if response.plan_steps:
                        self._append_text("\n[Execution Plan]\n", "plan_title")
                        for i, step in enumerate(response.plan_steps, 1):
                            args_str = ", ".join(f"{k}='{v}'" for k, v in step["arguments"].items())
                            self._append_text(f"  {i}. {step['tool']}({args_str})\n", "plan_step")
                        self._append_text("\n")

                    # Print Step Results
                    for res in response.execution_results:
                        if res.cancelled:
                            self._append_text(f"  [CANCELLED] {res.tool_name}: Action was cancelled.\n", "cancelled")
                        elif res.success:
                            self._append_text(f"  [SUCCESS] {res.tool_name}: {res.tool_result.message}\n", "success")
                            if res.verification.verified:
                                self._append_text(f"            {res.verification.details}\n", "cmd_header")
                        else:
                            self._append_text(f"  [FAILED] {res.tool_name}: {res.error}\n", "failed")

                    # Animate Typewriter Agent Response
                    self._append_text("\n[Agent Response]\n", "prompt_label")
                    self._typewriter_effect(response.final_response + "\n\n")

                    self.is_processing = False
                    self.cmd_entry.config(state=tk.NORMAL)
                    self.cmd_entry.focus_set()

                elif msg_type == "AGENT_ERROR":
                    self._append_text(f"\n[ERROR] {data}\n\n", "failed")
                    self.is_processing = False
                    self.cmd_entry.config(state=tk.NORMAL)
                    self.cmd_entry.focus_set()

        except queue.Empty:
            pass

        self.root.after(40, self._process_queue)

    def _typewriter_effect(self, text: str, delay_ms: int = 8):
        """Animates output text with a smooth typewriter typing effect."""
        def type_char(index):
            if index < len(text):
                chunk = text[index:index+3]
                self._append_text(chunk, "agent_response")
                self.root.after(delay_ms, lambda: type_char(index + 3))

        type_char(0)

    def _on_history_up(self, event):
        """Navigate previous commands with Up arrow."""
        if self.history_list and self.history_index > 0:
            self.history_index -= 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self.history_list[self.history_index])
        return "break"

    def _on_history_down(self, event):
        """Navigate next commands with Down arrow."""
        if self.history_list and self.history_index < len(self.history_list) - 1:
            self.history_index += 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self.history_list[self.history_index])
        elif self.history_index >= len(self.history_list) - 1:
            self.history_index = len(self.history_list)
            self.cmd_entry.delete(0, tk.END)
        return "break"


def launch_gui():
    """Launches the Animated Tkinter CMD Desktop Window."""
    root = tk.Tk()
    app = AnimatedTerminalGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
