#!/usr/bin/env python3
"""
Groq + DuckDuckGo Autonomous Coding Agent
=========================================
A complete, self-contained coding agent powered by:
  - Groq LLM API (`llama-3.3-70b-versatile` via LangGraph / ChatGroq)
    Docs: https://console.groq.com/docs/model/llama-3.3-70b-versatile
  - DuckDuckGo Web & Documentation Search (`ddgs` / `DuckDuckGoSearchRun`)
    Docs: https://pypi.org/project/duckduckgo-search/
          https://reference.langchain.com/python/langchain-community/tools/ddg_search/tool/DuckDuckGoSearchRun
  - Local Sandboxed Workspace Tools (file read/write, surgical patch edit,
    AST syntax check, and isolated subprocess test runner)

Quick Start:
------------
1. Install dependencies:
   pip install -U langgraph langchain-groq langchain-core langchain-community ddgs groq

2. Run interactive CLI mode:
   python groq_coding_agent.py

3. Or run a single task directly:
   python groq_coding_agent.py --task "Search DuckDuckGo for FastAPI lifespan events and write a main.py example"
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TypedDict


# ---------------------------------------------------------------------------
# 1. API Key Configuration & Normalization
# ---------------------------------------------------------------------------
# Groq keys must begin with lowercase `gsk_`. If a key was pasted with a
# capitalized `Gsk_` prefix (mobile/keyboard auto-capitalization), normalize it.
DEFAULT_PROVIDED_KEY = ""  # Loaded automatically from .env or GROQ_API_KEY environment variable


def _load_dotenv_if_present() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def resolve_groq_api_key(raw_key: Optional[str] = None) -> str:
    """Resolve and normalize the Groq API key (`gsk_...`)."""
    _load_dotenv_if_present()
    candidate = (raw_key or os.environ.get("GROQ_API_KEY") or DEFAULT_PROVIDED_KEY).strip()
    if candidate.startswith("Gsk_"):
        candidate = "g" + candidate[1:]
    os.environ["GROQ_API_KEY"] = candidate
    return candidate


# Workspace root where the coding agent is permitted to read/write/execute code
WORKSPACE_DIR = Path(os.environ.get("AGENT_WORKSPACE", "./agent_workspace")).resolve()
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_workspace_path(rel_path: str) -> Path:
    """Ensure file operations stay strictly inside WORKSPACE_DIR."""
    target = (WORKSPACE_DIR / rel_path).resolve()
    if not str(target).startswith(str(WORKSPACE_DIR)):
        raise ValueError(f"Access denied: '{rel_path}' is outside {WORKSPACE_DIR}")
    return target


# ---------------------------------------------------------------------------
# 2. Core Coding Agent Tools (DuckDuckGo Search + File System + Code Runner)
# ---------------------------------------------------------------------------
def search_duckduckgo(query: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo for live developer documentation, stack traces,
    package versions, or code examples. Requires zero API key.
    """
    # Primary path: `ddgs` / `duckduckgo_search` direct structured results
    try:
        try:
            from ddgs import DDGS  # New package name: https://pypi.org/project/ddgs/
        except ImportError:
            from duckduckgo_search import DDGS  # Fallback package name

        results = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href", item.get("link", "")),
                        "snippet": item.get("body", item.get("snippet", "")),
                    }
                )
        if results:
            return json.dumps(results, indent=2)
    except Exception:
        pass

    # Fallback path: LangChain's DuckDuckGoSearchRun wrapper
    try:
        from langchain_community.tools import DuckDuckGoSearchRun

        runner = DuckDuckGoSearchRun()
        return str(runner.invoke(query))
    except Exception as exc:
        return f"DuckDuckGo search error: {exc}. Ensure `pip install -U ddgs` is installed."


def list_workspace_files(subdir: str = ".") -> str:
    """List all files inside the agent workspace directory."""
    try:
        base = _safe_workspace_path(subdir)
        if not base.exists():
            return f"Directory '{subdir}' does not exist."
        files = [
            str(p.relative_to(WORKSPACE_DIR))
            for p in sorted(base.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts
        ]
        return "\n".join(files) if files else "(workspace is currently empty)"
    except Exception as exc:
        return f"Error listing files: {exc}"


def read_workspace_file(file_path: str, start_line: int = 1, end_line: int = 250) -> str:
    """Read lines from a file inside the agent workspace with line numbers."""
    try:
        target = _safe_workspace_path(file_path)
        if not target.exists():
            return f"Error: File '{file_path}' does not exist."
        lines = target.read_text(encoding="utf-8").splitlines()
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        numbered = [f"{i + 1:4d} | {lines[i]}" for i in range(start_idx, end_idx)]
        return "\n".join(numbered) if numbered else "(empty file)"
    except Exception as exc:
        return f"Error reading '{file_path}': {exc}"


def write_workspace_file(file_path: str, content: str) -> str:
    """Write or overwrite a file in the agent workspace and validate Python syntax if `.py`."""
    try:
        target = _safe_workspace_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        if target.suffix == ".py":
            try:
                ast.parse(content, filename=str(target))
                return f"Successfully wrote '{file_path}' ({len(content)} bytes) — AST syntax valid."
            except SyntaxError as syn_err:
                return (
                    f"Wrote '{file_path}', but Python AST check caught a SyntaxError at "
                    f"line {syn_err.lineno}: {syn_err.msg}"
                )
        return f"Successfully wrote '{file_path}' ({len(content)} bytes)."
    except Exception as exc:
        return f"Error writing '{file_path}': {exc}"


def patch_workspace_file(file_path: str, search_block: str, replace_block: str) -> str:
    """Replace an exact snippet (`search_block`) with `replace_block` in an existing file."""
    try:
        target = _safe_workspace_path(file_path)
        if not target.exists():
            return f"Error: File '{file_path}' not found."
        original = target.read_text(encoding="utf-8")
        if search_block not in original:
            return f"Error: `search_block` was not found verbatim in '{file_path}'. Read the file first."
        updated = original.replace(search_block, replace_block, 1)
        return write_workspace_file(file_path, updated)
    except Exception as exc:
        return f"Error patching '{file_path}': {exc}"


def run_python_code(script_or_command: str, is_file_path: bool = False, timeout_sec: int = 20) -> str:
    """
    Execute a Python file or inline snippet inside the isolated `WORKSPACE_DIR`
    and return `stdout`, `stderr`, and the exit code for automated self-debugging.
    """
    try:
        if is_file_path:
            target = _safe_workspace_path(script_or_command)
            cmd = [sys.executable, str(target)]
        else:
            cmd = [sys.executable, "-c", script_or_command]

        proc = subprocess.run(
            cmd,
            cwd=str(WORKSPACE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return json.dumps(
            {
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
            },
            indent=2,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"exit_code": -1, "error": f"Execution timed out after {timeout_sec}s."})
    except Exception as exc:
        return json.dumps({"exit_code": -1, "error": str(exc)})


# ---------------------------------------------------------------------------
# 3. System Prompt for the Autonomous Coding Agent
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an autonomous AI Coding Agent powered by Groq and DuckDuckGo Search.
You operate inside a dedicated local workspace directory and follow a strict Plan -> Research -> Code -> Test -> Fix loop:

1. **Research When Needed**: Whenever a task involves unfamiliar libraries, APIs, error messages, or current documentation, call `search_duckduckgo` first.
2. **Inspect Before Editing**: Use `list_workspace_files` and `read_workspace_file` to inspect existing code before modifying it.
3. **Write Clean, Modular Code**: Use `write_workspace_file` to create new files or `patch_workspace_file` for targeted edits.
4. **Always Verify via Execution**: After writing or modifying Python code, run it (or its test suite) using `run_python_code`. If `exit_code != 0` or `stderr` shows a traceback, analyze the error, fix the file, and re-run until tests pass.
5. **Summarize Clearly**: Once verified, explain what files were created or updated and show the verification output.
"""


# ---------------------------------------------------------------------------
# 4. Engine A: LangGraph + ChatGroq Stateful Agent (Primary Stack)
# ---------------------------------------------------------------------------
def build_langgraph_coding_agent(model_name: str = "llama-3.3-70b-versatile"):
    """
    Build a stateful LangGraph coding agent using `ChatGroq` and structured tools.
    Reference:
      - https://docs.langchain.com/oss/python/langgraph/overview
      - https://docs.langchain.com/oss/python/integrations/chat/groq
    """
    from langchain_core.messages import BaseMessage, SystemMessage
    from langchain_core.tools import tool
    from langchain_groq import ChatGroq
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode, tools_condition

    @tool
    def ddg_search(query: str, max_results: int = 5) -> str:
        """Search DuckDuckGo for documentation, APIs, code snippets, or bug fixes."""
        return search_duckduckgo(query=query, max_results=max_results)

    @tool
    def list_files(subdir: str = ".") -> str:
        """List all files inside the coding workspace."""
        return list_workspace_files(subdir=subdir)

    @tool
    def read_file(file_path: str, start_line: int = 1, end_line: int = 250) -> str:
        """Read lines from a file inside the coding workspace."""
        return read_workspace_file(file_path=file_path, start_line=start_line, end_line=end_line)

    @tool
    def write_file(file_path: str, content: str) -> str:
        """Create or overwrite a file in the workspace and check Python syntax."""
        return write_workspace_file(file_path=file_path, content=content)

    @tool
    def patch_file(file_path: str, search_block: str, replace_block: str) -> str:
        """Replace an exact code block in an existing workspace file."""
        return patch_workspace_file(
            file_path=file_path, search_block=search_block, replace_block=replace_block
        )

    @tool
    def execute_python(script_or_command: str, is_file_path: bool = False) -> str:
        """Run a Python file (is_file_path=True) or inline snippet (is_file_path=False) in the workspace."""
        return run_python_code(script_or_command=script_or_command, is_file_path=is_file_path)

    tools = [ddg_search, list_files, read_file, write_file, patch_file, execute_python]

    llm = ChatGroq(
        model=model_name,
        temperature=0.1,
        max_tokens=4096,
        api_key=resolve_groq_api_key(),
    ).bind_tools(tools)

    class AgentState(TypedDict):
        messages: Annotated[List[BaseMessage], add_messages]

    def reason_node(state: AgentState) -> Dict[str, Any]:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        response = llm.invoke(messages)
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", reason_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# ---------------------------------------------------------------------------
# 5. Engine B: Native Groq SDK Tool-Calling Loop (Zero-Framework Fallback)
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_duckduckgo",
            "description": "Search DuckDuckGo for live developer docs, APIs, and stack traces.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_workspace_files",
            "description": "List all files in the coding agent workspace.",
            "parameters": {
                "type": "object",
                "properties": {"subdir": {"type": "string", "default": "."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_workspace_file",
            "description": "Read a file from the workspace with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "start_line": {"type": "integer", "default": 1},
                    "end_line": {"type": "integer", "default": 250},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_workspace_file",
            "description": "Create or overwrite a code file in the workspace and run AST syntax check.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patch_workspace_file",
            "description": "Replace an exact snippet in a file with updated code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "search_block": {"type": "string"},
                    "replace_block": {"type": "string"},
                },
                "required": ["file_path", "search_block", "replace_block"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_code",
            "description": "Run a Python script or snippet and capture stdout, stderr, and exit_code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_or_command": {"type": "string"},
                    "is_file_path": {"type": "boolean", "default": False},
                },
                "required": ["script_or_command"],
            },
        },
    },
]

TOOL_DISPATCH = {
    "search_duckduckgo": search_duckduckgo,
    "list_workspace_files": list_workspace_files,
    "read_workspace_file": read_workspace_file,
    "write_workspace_file": write_workspace_file,
    "patch_workspace_file": patch_workspace_file,
    "run_python_code": run_python_code,
}


def run_native_groq_agent(
    user_prompt: str,
    history: List[Dict[str, Any]],
    model_name: str = "llama-3.3-70b-versatile",
    max_steps: int = 10,
) -> str:
    """Run the tool-calling loop directly with the official `groq` Python SDK."""
    from groq import Groq

    client = Groq(api_key=resolve_groq_api_key())
    if not history:
        history.append({"role": "system", "content": SYSTEM_PROMPT})
    history.append({"role": "user", "content": user_prompt})

    for step in range(1, max_steps + 1):
        response = client.chat.completions.create(
            model=model_name,
            messages=history,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=4096,
        )
        msg = response.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        if not tool_calls:
            final_text = msg.content or ""
            history.append({"role": "assistant", "content": final_text})
            return final_text

        history.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                fn_args = {}
            print(f"  [Step {step} Tool] -> {fn_name}({fn_args})")
            fn = TOOL_DISPATCH.get(fn_name)
            result = fn(**fn_args) if fn else f"Unknown tool: {fn_name}"
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": fn_name,
                    "content": str(result),
                }
            )

    return "Reached maximum tool-calling iterations."


# ---------------------------------------------------------------------------
# 6. CLI Entrypoint (Supports Both LangGraph and Native Groq SDK)
# ---------------------------------------------------------------------------
def run_task(prompt: str, model_name: str = "llama-3.3-70b-versatile", thread_id: str = "dev-session-1") -> str:
    """Execute a coding prompt using LangGraph if installed, otherwise the native Groq SDK."""
    try:
        from langchain_core.messages import HumanMessage

        graph = build_langgraph_coding_agent(model_name=model_name)
        config = {"configurable": {"thread_id": thread_id}}
        final_message = ""
        for event in graph.stream(
            {"messages": [HumanMessage(content=prompt)]},
            config=config,
            stream_mode="values",
        ):
            last_msg = event["messages"][-1]
            tool_calls = getattr(last_msg, "tool_calls", None)
            if tool_calls:
                for tc in tool_calls:
                    print(f"  [LangGraph Tool] -> {tc['name']}({tc['args']})")
            elif getattr(last_msg, "content", None) and last_msg.type == "ai":
                final_message = last_msg.content
        return final_message
    except ImportError:
        history: List[Dict[str, Any]] = []
        return run_native_groq_agent(prompt, history=history, model_name=model_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Groq + DuckDuckGo Coding Agent")
    parser.add_argument("--task", type=str, default=None, help="Run a single coding task and exit")
    parser.add_argument(
        "--model",
        type=str,
        default="llama-3.3-70b-versatile",
        help="Groq model ID (default: llama-3.3-70b-versatile)",
    )
    parser.add_argument("--api-key", type=str, default=None, help="Optional Groq API key override")
    args = parser.parse_args()

    active_key = resolve_groq_api_key(args.api_key)
    masked_key = f"{active_key[:8]}...{active_key[-4:]}"
    print(f"=== Groq + DuckDuckGo Coding Agent ===")
    print(f"Model     : {args.model}")
    print(f"API Key   : {masked_key} (normalized prefix: {active_key[:4]})")
    print(f"Workspace : {WORKSPACE_DIR}\n")

    if args.task:
        answer = run_task(args.task, model_name=args.model)
        print(f"\n[Agent Response]\n{answer}")
        return

    print("Interactive mode ready. Type 'exit' or 'quit' to stop.\n")
    native_history: List[Dict[str, Any]] = []
    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break
        try:
            try:
                reply = run_task(user_input, model_name=args.model)
            except Exception:
                reply = run_native_groq_agent(user_input, history=native_history, model_name=args.model)
            print(f"\nAgent >\n{reply}\n")
        except Exception as err:
            print(f"\n[Error] {err}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
