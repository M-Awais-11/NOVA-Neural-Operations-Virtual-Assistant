# Local AI Desktop Agent (Phase 1 & Phase 2 MVP)

A secure, modular, and extensible **Local AI Desktop Agent** for Windows that safely executes natural-language tasks on your PC using **OpenRouter (Free Models)** / OpenAI tool calling, strict allowlist sandboxing, user confirmation gating, and post-execution verification.

---

## 🌟 Key Features

* **AI Brain (Phase 1)**: Converts user requests into structured tool calls using OpenRouter Free Models (`meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash:free`, etc.) or OpenAI endpoints.
* **Allowlisted Tool System (Phase 2)**:
  * `create_folder`: Safe folder creation in allowed directories.
  * `create_file`: Safe text file creation with overwrite protection.
  * `read_file`: Safe file reading with size limits and UTF-8 handling.
  * `list_directory`: Lists files & folders with metadata (sizes, timestamps).
  * `search_files`: Fast recursive file search with pattern/extension filters.
  * `open_application`: Opens safe allowlisted apps (`notepad`, `calc`, `paint`, `explorer`).
* **Sandboxed Security Layer**:
  * Restricts access strictly to allowed user areas (`Desktop`, `Documents`, `Downloads`, and `AI_Agent_Workspace`).
  * Blocks path traversal (`..`), Windows system paths (`C:\Windows`, `System32`), and sensitive files (`.env`, `.ssh`, `.key`, `id_rsa`).
  * Enforces interactive confirmation for risky operations.
* **Execution & Verification**:
  * Two-step verification: checks actual disk/process status before reporting success.
* **SQLite Memory**:
  * Logs commands, tool arguments, execution statuses, and auto-redacts sensitive keys/passwords.

---

## 📁 Project Structure

```text
AI AGENT/
│
├── main.py                     # Interactive CLI interface
├── requirements.txt            # Python dependencies
├── .env.example                # Configuration template
├── .env                        # Active environment configuration
├── README.md                   # Documentation
│
├── config/                     # Configuration & settings
│   ├── __init__.py
│   └── settings.py
│
├── security/                   # Sandboxing, permissions & confirmations
│   ├── __init__.py
│   ├── permissions.py
│   ├── confirmation.py
│   └── path_validator.py
│
├── tools/                      # Allowlisted tool definitions & registry
│   ├── __init__.py
│   ├── base.py
│   ├── file_tools.py
│   ├── app_tools.py
│   └── registry.py
│
├── agent/                      # Core AI pipeline
│   ├── __init__.py
│   ├── planner.py              # LLM tool call generator (OpenRouter HTTP)
│   ├── executor.py             # Tool execution & confirmation gate
│   ├── verifier.py             # Post-execution outcome checker
│   └── agent.py                # Main orchestrator
│
├── memory/                     # Persistent SQLite memory
│   ├── __init__.py
│   └── memory.py
│
└── tests/                      # Automated test suite (19 passed unit tests)
    ├── __init__.py
    ├── test_security.py
    ├── test_tools.py
    └── test_agent.py
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.11 or higher
- An **OpenRouter Free API Key** (Get one free at [openrouter.ai/keys](https://openrouter.ai/keys))

### 2. Setup & Configuration

1. Open `.env` file in the project folder and paste your OpenRouter key:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-your-free-key-here
   OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   ```

2. Popular Free Models you can use:
   * `meta-llama/llama-3.3-70b-instruct:free` (Default, excellent at tool calling)
   * `google/gemini-2.0-flash:free`
   * `google/gemini-2.0-flash-lite:free`
   * `mistralai/mistral-small-3.1-24b-instruct:free`
   * `qwen/qwen-2.5-72b-instruct:free`

### 3. Run the Agent

Launch the CLI:
```powershell
python main.py
```

---

## 💬 Example Commands to Try

| Category | Example Command |
| :--- | :--- |
| **Create Folder** | `Create a folder named AI Projects on my Desktop` |
| **Create File** | `Create a text file inside Desktop/AI Projects called notes.txt with text "Learning AI Agents"` |
| **Read & Summarize**| `Read notes.txt from Desktop/AI Projects and summarize it` |
| **List Directory** | `List all files inside my Desktop` |
| **Search Files** | `Search for all .txt files on my Desktop` |
| **Open App** | `Open Notepad` or `Open Calculator` |
| **Multi-Step** | `Create a folder called Data on my Desktop and create a file summary.txt inside it.` |
| **Special CLI** | `history` (view SQLite history), `help`, `clear`, `exit` |

---

## 🧪 Running Automated Tests

Run the full test suite with pytest:

```powershell
python -m pytest tests/ -v
```

---

## 🔒 Security Architecture

1. **Strict Path Sandboxing**:
   The AI agent cannot access or write to any directory outside the allowlisted roots:
   - User's Desktop
   - User's Documents
   - User's Downloads
   - `AI_Agent_Workspace`
2. **Blocked System Paths & Traversal**:
   Paths such as `C:\Windows`, `C:\Program Files`, `..\..\`, and `.ssh` are rejected before any OS operation is attempted.
3. **No Arbitrary Shell Execution**:
   The agent does NOT possess arbitrary bash/cmd execution tools. Only predefined Python functions and specific allowlisted applications (`notepad.exe`, `calc.exe`, etc.) can be launched with `shell=False`.
4. **Credential Redaction in Memory**:
   Any detected API key or password pattern is redacted prior to writing to the SQLite database.
