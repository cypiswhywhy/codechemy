#!/usr/bin/env python3
"""
mcp-audit hook — runs on BOTH PreToolUse and PostToolUse.

Fires only for MCP tools (matcher "^mcp__" in hooks.json). This script then
filters to the servers the user chose in their config and appends one JSONL
line per event to a durable log.

Design notes:
- Observe-only. NEVER blocks. Always exits 0, even on internal error.
- Pre and Post are correlated via `tool_use_id` (provided by Claude Code),
  so duration_ms and outcome can be joined later even under concurrency.
- If there is no config, or the calling server is not in the config, this
  script does nothing and produces no output.
- tool_input is captured but truncated to `truncate_bytes` to bound log size
  and limit exposure of sensitive content.

Log + config + state all live under MCP_AUDIT_HOME (default ~/.claude/mcp-audit).
"""

import sys
import os
import json
import time
import socket
import getpass
import pathlib
from datetime import datetime, timezone


def audit_home() -> pathlib.Path:
    h = os.environ.get("MCP_AUDIT_HOME")
    if h:
        return pathlib.Path(os.path.expanduser(h))
    return pathlib.Path(os.path.expanduser("~/.claude/mcp-audit"))


def load_config(base: pathlib.Path):
    """Return config dict, or None if not configured (=> no-op)."""
    cfg_path = base / "config.json"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            user = json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None
    cfg = {
        "servers": [],
        "truncate_bytes": 2048,
        "enabled": True,
        "log_path": str(base / "mcp-invocations.jsonl"),
    }
    for k, v in (user or {}).items():
        if v is not None:
            cfg[k] = v
    return cfg


def match_server(tool_name: str, servers):
    """Return the configured server name that owns this tool, else None.

    Anchored on the full `mcp__<server>__` prefix so a target of "asana"
    never accidentally matches "asana-clone".
    """
    for s in servers:
        if tool_name.startswith("mcp__%s__" % s):
            return s
    return None


def truncate_input(tool_input, limit: int):
    """Return (value_to_log, was_truncated)."""
    try:
        s = json.dumps(tool_input, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        s = str(tool_input)
    encoded = s.encode("utf-8")
    if len(encoded) <= limit:
        return tool_input, False
    clipped = encoded[:limit].decode("utf-8", "ignore")
    return {"_truncated": True, "preview": clipped}, True


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def append_line(log_path: str, record: dict):
    """Append one JSONL line with an advisory lock (best-effort)."""
    log_path = os.path.expanduser(log_path)
    pathlib.Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        try:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass
        f.write(line)
        f.flush()


def detect_status(tool_response):
    """Best-effort success/error classification of an MCP tool response."""
    if isinstance(tool_response, dict):
        if tool_response.get("isError") is True:
            return "error"
        if tool_response.get("is_error") is True:
            return "error"
        if "error" in tool_response and tool_response.get("error"):
            return "error"
    return "success"


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool_name = data.get("tool_name", "") or ""
    if not tool_name.startswith("mcp__"):
        return 0

    base = audit_home()
    cfg = load_config(base)
    if not cfg or not cfg.get("enabled", True):
        return 0

    servers = cfg.get("servers") or []
    server = match_server(tool_name, servers)
    if server is None:
        return 0

    event = data.get("hook_event_name", "") or ""
    session_id = data.get("session_id", "") or ""
    cwd = data.get("cwd", "") or ""
    tool_use_id = data.get("tool_use_id", "") or ""
    log_path = cfg.get("log_path")
    state_dir = base / "state"

    try:
        host = socket.gethostname()
    except Exception:
        host = ""
    try:
        user = getpass.getuser()
    except Exception:
        user = os.environ.get("USER", "")

    if event == "PreToolUse":
        tool_input, truncated = truncate_input(
            data.get("tool_input", {}), int(cfg.get("truncate_bytes", 2048))
        )
        record = {
            "event": "pre",
            "ts": now_iso(),
            "user": user,
            "host": host,
            "session_id": session_id,
            "tool_use_id": tool_use_id,
            "cwd": cwd,
            "server": server,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "input_truncated": truncated,
        }
        append_line(log_path, record)
        # Stash start time for duration_ms on the matching PostToolUse.
        if tool_use_id:
            try:
                state_dir.mkdir(parents=True, exist_ok=True)
                (state_dir / tool_use_id).write_text(str(time.time()))
            except Exception:
                pass
        return 0

    if event == "PostToolUse":
        duration_ms = None
        if tool_use_id:
            sf = state_dir / tool_use_id
            try:
                start = float(sf.read_text().strip())
                duration_ms = int(round((time.time() - start) * 1000))
            except Exception:
                duration_ms = None
            finally:
                try:
                    sf.unlink()
                except Exception:
                    pass
        record = {
            "event": "post",
            "ts": now_iso(),
            "user": user,
            "host": host,
            "session_id": session_id,
            "tool_use_id": tool_use_id,
            "cwd": cwd,
            "server": server,
            "tool_name": tool_name,
            "status": detect_status(data.get("tool_response")),
            "duration_ms": duration_ms,
        }
        append_line(log_path, record)
        return 0

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Observe-only: never let an audit failure disrupt the session.
        sys.exit(0)
