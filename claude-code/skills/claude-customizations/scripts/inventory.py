#!/usr/bin/env python3
"""Inventory every Claude Code customization on this machine. Stdlib only, read-only.

    python3 inventory.py                 # human-readable report
    python3 inventory.py --json          # the same data as JSON
    python3 inventory.py --project DIR   # project scope to inspect (default: cwd)
    python3 inventory.py --implicit      # only what shapes a session without the user invoking it

A fresh Claude Code install has no settings.json, CLAUDE.md, skills, agents, commands,
hooks, keybindings, plugins or MCP servers, and Claude Desktop has no MCP servers or
extensions. Everything this prints is therefore a customization, except the version
lines. Runtime state the app writes for itself (history, sessions, caches, telemetry)
is skipped; anything under the config dir that is neither is reported as unrecognized
so nothing can hide there.

--implicit keeps what acts on a session by itself: instructions (CLAUDE.md, rules, managed
settings), hooks that are registered, skills and commands the model may invoke (those without
`disable-model-invocation: true`), agents, enabled plugins, MCP servers, permissions, env vars
and scheduled tasks. UI preferences, marketplaces, disabled plugins, unregistered hook scripts,
keybindings, themes and leftover files are dropped.

Secrets never reach the output: values of keys that look like credentials, and env var
values in MCP server definitions, are redacted.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or HOME / ".claude")
GLOBAL_STATE = HOME / ".claude.json"
SYSTEM = platform.system()

# Entries under the config dir that carry a customization.
USER_FILES = ("settings.json", "settings.local.json", "CLAUDE.md", "CLAUDE.local.md", "keybindings.json")
USER_DIRS = ("skills", "commands", "agents", "hooks", "rules", "output-styles", "themes", "workflows", "scheduled-tasks", "plugins")

# Entries a fresh install or ordinary use writes for itself. Not customizations; skipped.
RUNTIME_ENTRIES = {
    ".credentials.json", ".DS_Store", ".last-cleanup", ".last-update-result.json", ".update.lock",
    "agent-memory", "backups", "cache", "credentials", "daemon", "debug", "downloads", "feedback",
    "feedback-bundles", "file-history", "history.jsonl", "ide", "image-cache", "jobs", "local", "logs",
    "paste-cache", "plans", "policy-limits.json", "projects", "remote-settings.json", "session-env",
    "sessions", "shell-snapshots", "stats-cache.json", "statsig", "tasks", "telemetry", "todos",
    "transcripts", "uploads", "usage-data", "versions",
}

# Keys in ~/.claude.json that a user sets (directly or via /config); the rest is runtime state.
GLOBAL_PREFERENCE_KEYS = (
    "autoUpdates", "autoConnectIde", "autoMemoryEnabled", "autoCompactEnabled", "diffTool", "editorMode",
    "externalEditorContext", "model", "preferredNotifChannel", "theme", "verbose",
)
PROJECT_STATE_KEYS = ("mcpServers", "allowedTools", "enabledMcpjsonServers", "disabledMcpjsonServers", "ignorePatterns")

# Environment variables that configure Claude Code, minus the ones it sets for its own session.
ENV_PREFIXES = ("ANTHROPIC_", "CLAUDE_", "DISABLE_", "MCP_", "OTEL_", "BASH_", "AWS_", "VERTEX_", "CLOUD_ML_")
ENV_EXACT = {"API_TIMEOUT_MS", "DO_NOT_TRACK", "HTTP_PROXY", "HTTPS_PROXY", "MAX_THINKING_TOKENS", "NO_PROXY", "USE_BUILTIN_RIPGREP"}
SESSION_ENV = {
    "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_EXECPATH", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_PID",
    "CLAUDE_EFFORT", "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_SSE_PORT", "CLAUDE_SKILL_DIR", "CLAUDE_PLUGIN_ROOT",
    "CLAUDE_PROJECT_DIR", "CLAUDE_ENV_FILE", "CLAUDE_AGENT_SDK_VERSION",
}

# settings.json keys that change the terminal UI, never what the agent sees or does.
# ~/.claude.json preferences that change what the agent does; the rest only change the interface.
STATE_BEHAVIOUR = {"model", "autoMemoryEnabled", "autoCompactEnabled"}
UI_SETTINGS = {"tui", "statusLine", "spinnerTipsEnabled", "showTurnDuration", "theme", "autoUpdatesChannel",
               "spinnerVerbs", "terminalProgressBarEnabled", "prefersReducedMotion", "respectGitignore"}

# Documented defaults: what a user who never set the item effectively gets. Keyed by scope
# ("settings", "state" for ~/.claude.json, "env"). Filled from the official settings and
# env-var references; an env var not listed here defaults to unset with no further effect noted.
DEFAULTS: dict[str, dict[str, str]] = {
    "settings": {
        "model": "unset (the account's default model)",
        "effortLevel": "unset (the model's own default)",
        "cleanupPeriodDays": "30",
        "alwaysThinkingEnabled": "true",
        "autoCompactEnabled": "true",
        "autoMemoryEnabled": "true",
        "showTurnDuration": "true",
        "spinnerTipsEnabled": "true",
        "respectGitignore": "true",
        "prefersReducedMotion": "false",
        "skipDangerousModePermissionPrompt": "false",
    },
    "state": {
        "autoConnectIde": "false",
        "diffTool": "terminal",
    },
    "env": {
        "CLAUDE_CODE_ENABLE_TELEMETRY": "unset (OpenTelemetry export off)",
        "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "unset (span tracing off)",
        "OTEL_METRICS_EXPORTER": "unset (no metrics exported)",
        "OTEL_LOGS_EXPORTER": "unset (no logs exported)",
        "OTEL_TRACES_EXPORTER": "unset (no traces exported)",
        "OTEL_METRIC_EXPORT_INTERVAL": "60000",
        "OTEL_LOGS_EXPORT_INTERVAL": "5000",
        "OTEL_LOG_USER_PROMPTS": "unset (prompts not logged)",
        "OTEL_LOG_TOOL_DETAILS": "unset (tool parameters not logged)",
        "OTEL_METRICS_INCLUDE_SESSION_ID": "true",
        "OTEL_METRICS_INCLUDE_VERSION": "false",
        "OTEL_METRICS_INCLUDE_ACCOUNT_UUID": "true",
        "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE": "delta",
        "DISABLE_TELEMETRY": "unset (Statsig usage telemetry on)",
        "DISABLE_ERROR_REPORTING": "unset (Sentry error reporting on)",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "unset (non-essential traffic allowed)",
        "BASH_DEFAULT_TIMEOUT_MS": "120000",
        "BASH_MAX_TIMEOUT_MS": "600000",
        "BASH_MAX_OUTPUT_LENGTH": "30000",
        "API_TIMEOUT_MS": "600000",
        "ANTHROPIC_MODEL": "unset (the account's default model)",
    },
}


def default_for(scope: str, key: str) -> str | None:
    if scope == "env":
        return DEFAULTS["env"].get(key, "unset")
    return DEFAULTS[scope].get(key)


ANSI = re.compile(r"\033\[[0-9;]*m")
SHELL_RC = (".zshenv", ".zprofile", ".zshrc", ".bash_profile", ".bashrc", ".profile", ".config/fish/config.fish")

SECRET_KEY = re.compile(r"(token|secret|key|password|passwd|credential|authorization|cookie)", re.I)
SECRET_VALUE = re.compile(r"^(sk-ant-|ghp_|github_pat_|xox[abp]-|Bearer )")
URL_USERINFO = re.compile(r"(?<=://)[^/@\s]+@")  # user:pass@ in proxy and MCP URLs

PROJECT_PATHS = (
    "CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".mcp.json", ".worktreeinclude",
    ".claude/settings.json", ".claude/settings.local.json", ".claude/CLAUDE.md",
    ".claude/commands", ".claude/skills", ".claude/agents", ".claude/hooks", ".claude/rules",
    ".claude/output-styles", ".claude/workflows",
)


def redact(key: str, value):
    if not isinstance(value, str):
        return value
    if SECRET_KEY.search(key) or SECRET_VALUE.match(value):
        return "<redacted>"
    return URL_USERINFO.sub("<redacted>@", value)


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return {"__error__": f"{type(exc).__name__}: {exc}"}


def frontmatter(path: Path) -> dict:
    """The name/description of a SKILL.md, command or agent file, or {} when it has none."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    head = text.split("---", 2)
    if len(head) < 3:
        return {}
    fields = {}
    for line in head[1].splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip("\"'")
    return fields


def describe_dir_entry(path: Path, doc: Path) -> dict:
    entry = {"name": path.name, "path": str(path)}
    if path.is_symlink():
        entry["link_target"] = os.readlink(path)
        entry["broken"] = not path.exists()
    if not entry.get("broken"):
        fields = frontmatter(doc)
        entry["description"] = fields.get("description", "")
        if fields.get("disable-model-invocation", "").lower() == "true":
            entry["user_only"] = True
    return entry


def mcp_servers(servers: dict) -> list[dict]:
    out = []
    for name, spec in sorted(servers.items()):
        if not isinstance(spec, dict):
            continue
        item = {"name": name}
        for key in ("type", "command", "url"):
            if key in spec:
                item[key] = redact(key, spec[key])
        if spec.get("args"):
            item["args"] = spec["args"]
        if spec.get("env"):
            item["env_keys"] = sorted(spec["env"])
        out.append(item)
    return out


# ----- scopes ----------------------------------------------------------------


def versions() -> dict:
    info = {"platform": f"{SYSTEM} {platform.release()} {platform.machine()}"}
    cli = shutil.which("claude")
    if cli:
        try:
            out = subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=15).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            out = f"error: {exc}"
        info["cli"] = {"path": cli, "version": out}
    if GLOBAL_STATE.exists():
        state = read_json(GLOBAL_STATE)
        if isinstance(state, dict) and "installMethod" in state:
            info["install_method"] = state["installMethod"]
    return info


def settings_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    data = read_json(path)
    if not isinstance(data, dict):
        return {"path": str(path), "error": "not a JSON object"}
    report = {"path": str(path)}
    if "env" in data and isinstance(data["env"], dict):
        report["env"] = {k: redact(k, v) for k, v in sorted(data["env"].items())}
    if "hooks" in data and isinstance(data["hooks"], dict):
        report["hooks"] = {
            event: [
                (f"[{group['matcher']}] " if group.get("matcher") else "") + str(h.get("command", h.get("type", "?")))
                for group in groups for h in group.get("hooks", [])
            ]
            for event, groups in sorted(data["hooks"].items())
        }
    if "permissions" in data and isinstance(data["permissions"], dict):
        report["permissions"] = data["permissions"]
    if "enabledPlugins" in data:
        report["enabled_plugins"] = sorted(k for k, v in data["enabledPlugins"].items() if v)
    if "extraKnownMarketplaces" in data:
        report["marketplaces"] = sorted(data["extraKnownMarketplaces"])
    structured = ("env", "hooks", "permissions", "enabledPlugins", "extraKnownMarketplaces")
    report["values"] = {k: redact(k, v) for k, v in sorted(data.items()) if k not in structured}
    report["defaults"] = {k: d for k in report["values"] if (d := default_for("settings", k))}
    return report


def markdown_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    text = path.read_text(errors="replace")
    headings = [line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#")]
    managed = re.findall(r"<!--\s*([\w-]+):begin\b([^>]*)-->", text)
    return {
        "path": str(path),
        "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        "headings": headings,
        "managed_blocks": [f"{name}{extra.split('(')[0].rstrip()}" for name, extra in managed],
        "includes": re.findall(r"^@(\S+)", text, re.M),
    }


def listing(directory: Path, doc_name: str | None) -> list[dict]:
    """Children of a customization directory. doc_name is the file that carries the frontmatter
    (SKILL.md for skill dirs); None means the children are themselves markdown files."""
    if not directory.is_dir():
        return []
    items = []
    for child in sorted(directory.iterdir()):
        if child.name.startswith("."):
            continue
        doc = child / doc_name if doc_name else child
        items.append(describe_dir_entry(child, doc))
    return items


def hooks_dir(registered: dict) -> list[dict]:
    directory = CONFIG_DIR / "hooks"
    if not directory.is_dir():
        return []
    commands = " ".join(cmd for cmds in registered.values() for cmd in cmds)
    return [
        {"name": p.name, "path": str(p), "registered": p.name in commands}
        for p in sorted(directory.iterdir()) if p.is_file() and not p.name.startswith(".")
    ]


def plugins(enabled: list[str]) -> dict:
    root = CONFIG_DIR / "plugins"
    installed = read_json(root / "installed_plugins.json") if (root / "installed_plugins.json").exists() else {}
    marketplaces = read_json(root / "known_marketplaces.json") if (root / "known_marketplaces.json").exists() else {}
    plugin_list = []
    for name, entries in sorted((installed.get("plugins") or {}).items()):
        for entry in entries if isinstance(entries, list) else [entries]:
            plugin_list.append({
                "name": name, "scope": entry.get("scope"), "version": entry.get("version"),
                "enabled": name in enabled, "install_path": entry.get("installPath"),
                "present": bool(entry.get("installPath")) and Path(entry["installPath"]).exists(),
            })
    installed_names = {p["name"] for p in plugin_list}
    return {
        "installed": plugin_list,
        "enabled_but_not_installed": sorted(set(enabled) - installed_names),
        "marketplaces": [
            {"name": name, **{k: v for k, v in (spec.get("source") or {}).items()}, "auto_update": spec.get("autoUpdate", False)}
            for name, spec in sorted(marketplaces.items()) if isinstance(spec, dict) and not name.startswith("__")
        ],
    }


def global_state() -> dict | None:
    if not GLOBAL_STATE.exists():
        return None
    data = read_json(GLOBAL_STATE)
    if not isinstance(data, dict):
        return {"path": str(GLOBAL_STATE), "error": "not a JSON object"}
    projects = {}
    for path, state in sorted((data.get("projects") or {}).items()):
        if not isinstance(state, dict):
            continue
        custom = {k: state[k] for k in PROJECT_STATE_KEYS if state.get(k)}
        if "mcpServers" in custom:
            custom["mcpServers"] = mcp_servers(custom["mcpServers"])
        if custom:
            projects[path] = custom
    return {
        "path": str(GLOBAL_STATE),
        "preferences": {k: redact(k, data[k]) for k in GLOBAL_PREFERENCE_KEYS if k in data},
        "preference_defaults": {k: d for k in GLOBAL_PREFERENCE_KEYS if k in data and (d := default_for("state", k))},
        "mcp_servers": mcp_servers(data.get("mcpServers") or {}),
        "projects_with_customizations": projects,
        "known_projects": len(data.get("projects") or {}),
    }


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def unrecognized(owners: dict[str, str]) -> list[dict]:
    """Config-dir entries that are neither a known customization nor runtime state. `owners` maps a
    slug (managed block name, hook script stem) to a label, so an installer's state file or per-hook
    state dir is attributed rather than flagged."""
    if not CONFIG_DIR.is_dir():
        return []
    known = set(USER_FILES) | set(USER_DIRS) | RUNTIME_ENTRIES
    entries = []
    for path in sorted(CONFIG_DIR.iterdir()):
        if path.name in known:
            continue
        base = slug(path.name.split(".")[0])
        owner = next((label for token, label in owners.items() if base and (token.startswith(base) or base.startswith(token))), None)
        entries.append({
            "name": path.name + ("/" if path.is_dir() else ""),
            "backup": path.name.startswith("settings.json."),
            "owner": None if path.name.startswith("settings.json.") else owner,
        })
    return entries


def user_scope() -> dict:
    settings = settings_file(CONFIG_DIR / "settings.json")
    registered_hooks = (settings or {}).get("hooks", {})
    enabled_plugins = (settings or {}).get("enabled_plugins", [])
    skills = listing(CONFIG_DIR / "skills", "SKILL.md")
    for skill in skills:
        skill["has_skill_md"] = (Path(skill["path"]) / "SKILL.md").exists()
    claude_md = markdown_file(CONFIG_DIR / "CLAUDE.md")
    hook_scripts = hooks_dir(registered_hooks)
    owners = {slug(block.split()[0]): f"the {block.split()[0]} bundle" for block in (claude_md or {}).get("managed_blocks", [])}
    owners.update({slug(Path(h["name"]).stem): f"hook script {h['name']}" for h in hook_scripts})
    return {
        "config_dir": str(CONFIG_DIR),
        "exists": CONFIG_DIR.is_dir(),
        "settings": settings,
        "settings_local": settings_file(CONFIG_DIR / "settings.local.json"),
        "claude_md": claude_md,
        "claude_local_md": markdown_file(CONFIG_DIR / "CLAUDE.local.md"),
        "keybindings": read_json(CONFIG_DIR / "keybindings.json") if (CONFIG_DIR / "keybindings.json").exists() else None,
        "skills": skills,
        "commands": listing(CONFIG_DIR / "commands", None),
        "agents": listing(CONFIG_DIR / "agents", None),
        "rules": listing(CONFIG_DIR / "rules", None),
        "output_styles": listing(CONFIG_DIR / "output-styles", None),
        "themes": listing(CONFIG_DIR / "themes", None),
        "workflows": listing(CONFIG_DIR / "workflows", None),
        "scheduled_tasks": listing(CONFIG_DIR / "scheduled-tasks", "SKILL.md"),
        "hook_scripts": hook_scripts,
        "plugins": plugins(enabled_plugins),
        "global_state": global_state(),
        "unrecognized": unrecognized(owners),
    }


def managed_scope() -> dict:
    roots = {
        "Darwin": [Path("/Library/Application Support/ClaudeCode")],
        "Linux": [Path("/etc/claude-code")],
        "Windows": [Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "ClaudeCode"],
    }.get(SYSTEM, [])
    found = {}
    for root in roots:
        candidates = [root / "managed-settings.json", root / "managed-mcp.json", *sorted((root / "managed-settings.d").glob("*.json"))]
        for path in candidates:
            if path.exists():
                data = read_json(path)
                found[str(path)] = sorted(data) if isinstance(data, dict) else "unreadable"
        if (root / "CLAUDE.md").exists():
            found[str(root / "CLAUDE.md")] = markdown_file(root / "CLAUDE.md")["headings"]
    return {"searched": [str(r) for r in roots], "files": found}


def is_config_var(name: str) -> bool:
    return name not in SESSION_ENV and (name.startswith(ENV_PREFIXES) or name in ENV_EXACT)


def environment(settings: dict | None) -> list[dict]:
    """Config env vars by source: the running process, settings.json's env block, and shell rc files.
    Run from inside Claude Code the process inherits settings.json's env, so the two overlap."""
    sources: dict[str, list[str]] = {}
    values = {name: os.environ[name] for name in os.environ if is_config_var(name)}
    for name in values:
        sources[name] = ["process"]
    for name, value in (settings or {}).get("env", {}).items():
        values.setdefault(name, str(value))
        sources.setdefault(name, []).append("settings.json")
    pattern = re.compile(r"^\s*(?:export\s+|set\s+-gx\s+)?([A-Z][A-Z0-9_]*)[= ]")
    for rc in SHELL_RC:
        path = HOME / rc
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            match = pattern.match(line)
            if match and is_config_var(match.group(1)):
                sources.setdefault(match.group(1), []).append(f"~/{rc}:{number}")
    return [
        {"name": name, "value": redact(name, values.get(name, "")), "sources": sorted(set(found)), "default": default_for("env", name)}
        for name, found in sorted(sources.items())
    ]


def desktop_scope() -> dict | None:
    root = {
        "Darwin": HOME / "Library/Application Support/Claude",
        "Windows": Path(os.environ.get("APPDATA", HOME / "AppData/Roaming")) / "Claude",
        "Linux": HOME / ".config/Claude",
    }.get(SYSTEM)
    if root is None or not root.is_dir():
        return None
    report = {"config_dir": str(root)}
    config_path = root / "claude_desktop_config.json"
    if config_path.exists():
        config = read_json(config_path)
        if isinstance(config, dict):
            report["config"] = {
                "keys": sorted(config),
                "mcp_servers": mcp_servers(config.get("mcpServers") or {}),
                "preferences": {k: redact(k, v) for k, v in sorted(config["preferences"].items())} if isinstance(config.get("preferences"), dict) else {},
            }
    extensions = root / "Claude Extensions"
    report["extensions"] = sorted(p.name for p in extensions.iterdir()) if extensions.is_dir() else []
    bundled = root / "claude-code"
    report["bundled_claude_code_versions"] = sorted(p.name for p in bundled.iterdir() if p.is_dir()) if bundled.is_dir() else []
    report["claude_code_env_vars_configured"] = (root / "ccd-environment-config.json").exists()
    return report


def project_scope(project: Path) -> dict:
    found = {}
    for rel in PROJECT_PATHS:
        path = project / rel
        if not path.exists():
            continue
        if path.is_dir():
            found[rel] = listing(path, "SKILL.md" if rel.endswith("skills") else None)
        elif path.name.endswith(".md"):
            found[rel] = markdown_file(path)
        elif path.name == ".mcp.json":
            data = read_json(path)
            found[rel] = mcp_servers(data.get("mcpServers") or {}) if isinstance(data, dict) else data
        elif path.name == ".worktreeinclude":
            found[rel] = path.read_text().split()
        else:
            found[rel] = settings_file(path)
    state = global_state() or {}
    return {
        "path": str(project),
        "files": found,
        "global_state_entry": (state.get("projects_with_customizations") or {}).get(str(project)),
    }


def inventory(project: Path) -> dict:
    user = user_scope()
    return {
        "versions": versions(),
        "user": user,
        "managed": managed_scope(),
        "environment": environment(user["settings"]),
        "desktop": desktop_scope(),
        "project": project_scope(project),
    }


# ----- implicit view ---------------------------------------------------------


def model_invocable(entries: list[dict]) -> list[dict]:
    return [e for e in entries if not e.get("user_only") and not e.get("broken")]


def implicit_settings(report: dict | None) -> dict | None:
    if not report or "error" in report:
        return report
    kept = {k: v for k, v in report.items() if k != "marketplaces"}
    kept["values"] = {k: v for k, v in report["values"].items() if k not in UI_SETTINGS}
    kept["defaults"] = {k: v for k, v in report["defaults"].items() if k in kept["values"]}
    return kept


def implicit_only(data: dict) -> dict:
    """Prune the inventory to what shapes a session without the user invoking it."""
    u = data["user"]
    active_style = ((u["settings"] or {}).get("values") or {}).get("outputStyle")
    u.update({
        "settings": implicit_settings(u["settings"]),
        "settings_local": implicit_settings(u["settings_local"]),
        "keybindings": None,
        "skills": model_invocable(u["skills"]),
        "commands": model_invocable(u["commands"]),
        "output_styles": [e for e in u["output_styles"] if Path(e["name"]).stem == active_style],
        "themes": [],
        "workflows": [],
        "hook_scripts": [h for h in u["hook_scripts"] if h["registered"]],
        "plugins": {"installed": [p for p in u["plugins"]["installed"] if p["enabled"]], "enabled_but_not_installed": [], "marketplaces": []},
        "unrecognized": [],
    })
    if u["global_state"]:
        u["global_state"]["preferences"] = {}
    if data["desktop"] and data["desktop"].get("config"):
        data["desktop"]["config"].update({"preferences": {}, "keys": ["mcpServers"]})
    files = data["project"]["files"]
    for rel in (".claude/skills", ".claude/commands"):
        if rel in files:
            files[rel] = model_invocable(files[rel])
    for rel, report in list(files.items()):
        if rel.startswith(".claude/settings"):
            files[rel] = implicit_settings(report)
    return data


# ----- text report -----------------------------------------------------------


HOME_AT_WORD_START = re.compile(r"""(?<![^\s"'=:,])""" + re.escape(str(HOME)))


def tilde(text: str) -> str:
    return HOME_AT_WORD_START.sub("~", text)


def version_key(version: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


def mcp_line(server: dict) -> str:
    target = server.get("url") or " ".join([server.get("command", ""), *server.get("args", [])]).strip()
    env = f"  env: {', '.join(server['env_keys'])}" if server.get("env_keys") else ""
    return f"{server['name']:<22} {target}{env}"


def first_sentence(text: str) -> str:
    return (text or "").split(". ")[0].rstrip(".")


def desktop_lags_cli(data: dict) -> bool:
    bundled = (data["desktop"] or {}).get("bundled_claude_code_versions") or []
    cli = (data["versions"].get("cli") or {}).get("version", "")
    return bool(bundled and cli) and max(map(version_key, bundled)) < version_key(cli)


class Terminal:
    """Shared rendering helpers: ruled sections, aligned rows, colour only on a TTY, counters."""

    def __init__(self) -> None:
        tty = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
        self.width = min(shutil.get_terminal_size((100, 20)).columns, 120) if tty else 100
        self.paint = (lambda code, text: f"\033[{code}m{text}\033[0m") if tty else (lambda code, text: text)
        self.items = 0
        self.warnings = 0

    def bold(self, text: str) -> str:
        return self.paint("1", text)

    def dim(self, text: str) -> str:
        return self.paint("2", text)

    def section(self, title: str, note: str = "") -> None:
        print(f"\n{self.paint('1;36', '▌ ' + title)}" + (f"  {self.dim(note)}" if note else ""))

    def group(self, title: str, note: str = "") -> None:
        print(f"\n  {self.bold(title)}" + (f"  {self.dim(note)}" if note else ""))

    def row(self, key: str, value: str = "", indent: int = 4, key_width: int = 14, count: bool = True, note: str = "") -> None:
        """One aligned line; `note` (e.g. the default) rides along when it fits, else goes on its own line."""
        text = f"{' ' * indent}{key:<{key_width}} {value}" if value else f"{' ' * indent}{key}"
        if note and len(ANSI.sub("", text + note)) < self.width:
            text, note = text + note, ""
        print(self.fit(text))
        if note:
            print(self.fit(" " * (indent + key_width + 1) + note.lstrip()))
        self.items += count

    def fit(self, text: str) -> str:
        plain = ANSI.sub("", text)
        if len(plain) < self.width:
            return text
        return plain[: self.width - 1] + "…"  # truncate the unstyled text so no escape sequence is cut in half

    def default_note(self, default: str | None, value=None) -> str:
        if not default:
            return ""
        if value is not None and str(value).lower() == default.lower():
            return self.dim("  (= default)")
        return self.dim(f"  default: {default}")

    def warn(self, message: str, indent: int = 4) -> None:
        print(self.fit(f"{' ' * indent}{self.paint('33', '⚠ ' + message)}"))
        self.warnings += 1

    def none(self, message: str) -> None:
        print(f"    {self.dim(message)}")


class EffectReport(Terminal):
    """Default layout: six questions (what is the agent told, how does it run, what runs on its own,
    what can it reach, what only changes the UI, what is left over), the source path as a column."""

    def __init__(self, data: dict, implicit: bool) -> None:
        super().__init__()
        self.data, self.implicit = data, implicit
        self.counts: dict[str, int] = {}
        u = data["user"]
        self.settings_files = [(f, tilde(f["path"])) for f in (u["settings"], u["settings_local"]) if f and "error" not in f]
        self.settings_files += [(r, rel) for rel, r in data["project"]["files"].items() if rel.startswith(".claude/settings") and r and "error" not in r]

    def begin(self, title: str, note: str) -> None:
        self.section(title, note)
        self.items = 0

    def close(self, title: str) -> None:
        self.counts[title] = self.items

    def source(self, text: str) -> str:
        return self.dim(f"   {tilde(text)}")

    def markdown(self, label: str, report: dict, indent_headings: bool = True) -> None:
        notes = [f"{report['lines']} lines"] + [f"managed block {b}" for b in report["managed_blocks"]] + [f"includes {i}" for i in report["includes"]]
        self.row(tilde(report["path"]), self.dim(" · ".join(notes)), key_width=40)
        for heading in report["headings"]:
            print(f"      {self.dim('#')} {heading}")

    def skills(self, title: str, entries: list[tuple[dict, str]]) -> None:
        if not entries:
            return
        print(f"    {title} ({len(entries)})")
        width = min(max(len(e["name"]) for e, _ in entries), 26)
        for entry, origin in entries:  # the source is only worth a note when it is not the standard directory
            location = tilde(entry["link_target"]) if "link_target" in entry else (origin if origin.startswith(".claude") else "")
            self.row(entry["name"], first_sentence(entry.get("description"))[:56], indent=6, key_width=width, note=self.source(location) if location else "")

    def render(self) -> None:
        d = self.data
        v, u, pr = d["versions"], d["user"], d["project"]
        print(self.bold("Claude Code customizations") + self.dim("  ·  everything that differs from a fresh install"))
        if self.implicit:
            print(self.dim("Implicit view: only what shapes a session without you invoking it. Run without --implicit for everything."))
        cli = f"CLI {v['cli']['version'].split()[0]} ({v.get('install_method', '?')})" if "cli" in v else "CLI not on PATH"
        bundled = (d["desktop"] or {}).get("bundled_claude_code_versions") or []
        desktop = f"Desktop bundles {', '.join(bundled)}" if bundled else ("Desktop not found" if d["desktop"] is None else "Desktop present")
        lag = self.paint("33", "  ⚠ older than the CLI") if desktop_lags_cli(d) else ""
        print(self.dim(f"{cli}  ·  {desktop}") + lag + self.dim(f"  ·  {v['platform']}"))
        self.warnings += bool(lag)

        # -- Instructions --
        self.begin("Instructions", "what every session is told")
        for report in (u["claude_md"], u["claude_local_md"]):
            if report:
                self.markdown("user", report)
        managed_md = {p: k for p, k in d["managed"]["files"].items() if p.endswith("CLAUDE.md")}
        for path, headings in managed_md.items():
            self.row(path, self.dim("managed"), key_width=40)
            for heading in headings:
                print(f"      {self.dim('#')} {heading}")
        if not managed_md:
            self.row("managed CLAUDE.md", self.dim("none"), key_width=40, count=False)
        project_md = [(rel, r) for rel, r in pr["files"].items() if rel.endswith(".md") and r]
        for rel, report in project_md:
            self.markdown(rel, report)
        if not project_md:
            self.row("project CLAUDE.md", self.dim(f"none in {tilde(pr['path'])}"), key_width=40, count=False)
        rules = [(e, tilde(str(CONFIG_DIR / "rules"))) for e in u["rules"]] + [(e, ".claude/rules") for e in pr["files"].get(".claude/rules", [])]
        self.skills("rules", rules)
        self.close("Instructions")

        # -- Behaviour --
        self.begin("Behaviour", "how the agent runs")
        for report, origin in self.settings_files:
            for key, value in report["values"].items():
                if key not in UI_SETTINGS:
                    self.row(key, json.dumps(value), key_width=16, note=self.source(origin) + self.default_note(report["defaults"].get(key), value))
            for kind, rules in report.get("permissions", {}).items():
                text = ", ".join(map(str, rules)) if isinstance(rules, list) else json.dumps(rules)
                self.row("permissions", f"{kind} {text}", key_width=16, note=self.source(origin))
        for path, keys in d["managed"]["files"].items():
            if not path.endswith("CLAUDE.md"):
                self.row("managed policy", f"{path}  {self.dim(', '.join(keys) if isinstance(keys, list) else keys)}", key_width=16)
        g = u["global_state"] or {"preferences": {}, "preference_defaults": {}, "projects_with_customizations": {}}
        for key, value in g["preferences"].items():
            if key in STATE_BEHAVIOUR:
                self.row(key, json.dumps(value), key_width=16, note=self.source(GLOBAL_STATE.as_posix()) + self.default_note(g["preference_defaults"].get(key), value))
        for path, custom in g["projects_with_customizations"].items():
            summary = ", ".join(f"{k} ×{len(v)}" for k, v in custom.items())
            self.row("project", f"{tilde(path)}  {self.dim(summary)}", key_width=16, note=self.source(GLOBAL_STATE.as_posix()))
        for item in d["environment"]:
            self.row("env", f"{item['name']}={item['value']}", key_width=4, note=self.source(", ".join(item["sources"])) + self.default_note(item["default"], item["value"]))
        if d["desktop"] and d["desktop"]["claude_code_env_vars_configured"]:
            self.row("Desktop env vars", "configured " + self.dim("(encrypted, contents not readable)"), key_width=16)
        active_style = next((r["values"].get("outputStyle") for r, _ in self.settings_files if r["values"].get("outputStyle")), None)
        if active_style:
            self.row("output style", str(active_style), key_width=16)
        if self.items == 0:
            self.none("none")
        self.close("Behaviour")

        # -- Automation --
        self.begin("Automation", "runs without you asking")
        for report, origin in self.settings_files:
            for event, commands in report.get("hooks", {}).items():
                for command in commands:
                    self.row("hook", f"{event:<14} {tilde(command)}", key_width=10, note=self.source(origin))
        for task in u["scheduled_tasks"]:
            self.row("scheduled", f"{task['name']}  {self.dim(first_sentence(task.get('description'))[:60])}", key_width=10)
        auto = [(e, tilde(str(CONFIG_DIR / "skills"))) for e in u["skills"] if not e.get("user_only") and not e.get("broken")]
        auto += [(e, tilde(str(CONFIG_DIR / "commands"))) for e in u["commands"] if not e.get("user_only") and not e.get("broken")]
        auto += [(e, rel) for rel in (".claude/skills", ".claude/commands") for e in pr["files"].get(rel, []) if not e.get("user_only") and not e.get("broken")]
        self.skills("skills the model may invoke on its own", auto)
        agents = [(e, tilde(str(CONFIG_DIR / "agents"))) for e in u["agents"]] + [(e, ".claude/agents") for e in pr["files"].get(".claude/agents", [])]
        self.skills("agents", agents)
        if self.items == 0:
            self.none("none")
        self.close("Automation")

        # -- Tools --
        self.begin("Tools", "what the agent can reach")
        marketplaces = {m["name"]: m for m in u["plugins"]["marketplaces"]}
        for plugin in u["plugins"]["installed"]:
            market = marketplaces.get(plugin["name"].rsplit("@", 1)[-1])
            origin = ""
            if market:
                src = market.get("repo") or market.get("url") or market.get("path") or market.get("source")
                origin = f"marketplace {src}" + (f"@{market['ref']}" if market.get("ref") else "") + (" (auto-update)" if market["auto_update"] else "")
            state = "" if plugin["enabled"] else "  disabled"
            self.row("plugin", f"{plugin['name']:<40} {plugin['version']}  {self.dim(plugin['scope'] + state)}", key_width=10, note=self.source(origin))
            if not plugin["present"]:
                self.warn("plugin files missing from the plugin cache", indent=8)
        for name in u["plugins"]["enabled_but_not_installed"]:
            self.warn(f"plugin {name} is enabled in settings.json but not installed")
        servers = [(s, GLOBAL_STATE.as_posix()) for s in (u["global_state"] or {}).get("mcp_servers", [])]
        servers += [(s, ".mcp.json") for s in pr["files"].get(".mcp.json", []) if isinstance(s, dict)]
        servers += [(s, "Claude Desktop") for s in ((d["desktop"] or {}).get("config") or {}).get("mcp_servers", [])]
        for server, origin in servers:
            self.row("mcp server", mcp_line(server), key_width=10, note=self.source(origin))
        for path in d["managed"]["files"]:
            if path.endswith("managed-mcp.json"):
                self.row("mcp server", f"defined by policy in {path}", key_width=10)
        if not servers:
            self.row("mcp servers", self.dim("none in ~/.claude.json, .mcp.json or Claude Desktop"), key_width=10, count=False)
        for ext in (d["desktop"] or {}).get("extensions", []):
            self.row("extension", f"{ext}  {self.dim('Claude Desktop')}", key_width=10)
        self.close("Tools")

        if self.implicit:
            self.summary()
            return

        # -- Interface --
        self.begin("Interface", "how it looks, not what it does")
        for report, origin in self.settings_files:
            for key, value in report["values"].items():
                if key in UI_SETTINGS:
                    self.row(key, json.dumps(value), key_width=16, note=self.source(origin) + self.default_note(report["defaults"].get(key), value))
        for key, value in g["preferences"].items():
            if key not in STATE_BEHAVIOUR:
                self.row(key, json.dumps(value), key_width=16, note=self.source(GLOBAL_STATE.as_posix()) + self.default_note(g["preference_defaults"].get(key), value))
        if u["keybindings"] is not None:
            self.row("keybindings", tilde(str(CONFIG_DIR / "keybindings.json")), key_width=16)
        manual = [(e, tilde(str(CONFIG_DIR / "skills"))) for e in u["skills"] if e.get("user_only")]
        manual += [(e, tilde(str(CONFIG_DIR / "commands"))) for e in u["commands"] if e.get("user_only")]
        self.skills("skills only you invoke", manual)
        self.skills("themes", [(e, tilde(str(CONFIG_DIR / "themes"))) for e in u["themes"]])
        self.skills("workflows", [(e, tilde(str(CONFIG_DIR / "workflows"))) for e in u["workflows"]])
        self.skills("output styles", [(e, tilde(str(CONFIG_DIR / "output-styles"))) for e in u["output_styles"]])
        cfg = ((d["desktop"] or {}).get("config") or {})
        prefs = cfg.get("preferences") or {}
        if prefs:
            sample = ", ".join(f"{k} {json.dumps(v)[:20]}" for k, v in list(prefs.items())[:4])
            self.row("Desktop prefs", f"{len(prefs)}  {self.dim(sample + ', …' if len(prefs) > 4 else sample)}", key_width=16)
        other = [k for k in cfg.get("keys", []) if k not in ("mcpServers", "preferences")]
        if other:
            self.row("Desktop keys", ", ".join(other), key_width=16)
        if self.items == 0:
            self.none("none")
        self.close("Interface")

        # -- Leftovers --
        self.begin("Leftovers", "nothing in Claude Code owns these")
        for script in u["hook_scripts"]:
            if not script["registered"]:
                self.warn(f"hook script {script['name']}   no settings.json event runs it   {tilde(str(CONFIG_DIR / 'hooks'))}")
                self.items += 1
        for entry in u["skills"] + u["commands"]:
            if entry.get("broken"):
                self.warn(f"broken link {entry['name']} → {tilde(entry['link_target'])}")
                self.items += 1
        backups = [e["name"] for e in u["unrecognized"] if e["backup"]]
        if backups:
            self.warn(f"{len(backups)} settings.json backups   {self.dim(', '.join(b.removeprefix('settings.json.') for b in backups))}")
            self.items += len(backups)
        for entry in u["unrecognized"]:
            if entry["backup"]:
                continue
            if entry["owner"]:
                self.row(entry["name"], self.dim(f"owned by {entry['owner']}"), key_width=40)
            else:
                self.warn(entry["name"])
                self.items += 1
        for path in g["projects_with_customizations"]:
            if not Path(path).exists():
                self.warn(f"remembered project no longer exists   {tilde(path)}")
                self.items += 1
        if self.items == 0:
            self.none("none")
        self.close("Leftovers")
        self.summary()

    def summary(self) -> None:
        c = self.counts
        shaping = sum(c.get(k, 0) for k in ("Instructions", "Behaviour", "Automation", "Tools"))
        parts = [f"{shaping} session-shaping items"]
        if not self.implicit:
            parts += [f"{c.get('Interface', 0)} interface-only", f"{c.get('Leftovers', 0)} leftovers"]
        flagged = self.paint("33", f"{self.warnings} flagged (⚠)") if self.warnings else "nothing flagged"
        self.section("Summary")
        print(f"    {'  ·  '.join(parts)}  ·  {flagged}\n")


class LocationReport(Terminal):
    """--by-location: one section per place a setting can come from, in override order."""

    def settings(self, title: str, report: dict | None, env: bool = True) -> None:
        """env=False for user-level settings, whose env block the Environment section already lists."""
        if not report:
            return
        self.group(title, tilde(report["path"]))
        if "error" in report:
            self.warn(report["error"])
            return
        for key, value in report["values"].items():
            self.row(key, json.dumps(value), note=self.default_note(report["defaults"].get(key), value))
        env_block = report.get("env", {})
        if env_block and not env:
            self.row("env", self.dim(f"{len(env_block)} variables, listed under Environment"), count=False)
        for name, value in env_block.items() if env else ():
            self.row("env", f"{name}={value}")
        for event, commands in report.get("hooks", {}).items():
            for command in commands:
                self.row("hooks", f"{event:<14} {tilde(command)}")
        for kind, rules in report.get("permissions", {}).items():
            self.row(f"permissions.{kind}" if len(kind) < 6 else kind, ", ".join(map(str, rules)) if isinstance(rules, list) else json.dumps(rules), key_width=17)
        if report.get("enabled_plugins"):
            self.row("plugins", ", ".join(report["enabled_plugins"]))
        if report.get("marketplaces"):
            self.row("marketplaces", ", ".join(report["marketplaces"]))

    def markdown(self, title: str, report: dict | None) -> None:
        if not report:
            return
        notes = [f"{report['lines']} lines"]
        notes += [f"managed block {b}" for b in report["managed_blocks"]]
        notes += [f"includes {i}" for i in report["includes"]]
        self.group(title, f"{tilde(report['path'])}  ·  {' · '.join(notes)}")
        self.items += 1
        for heading in report["headings"]:
            print(f"    {self.dim('#')} {heading}")

    def entries(self, title: str, entries: list[dict], hint: str = "") -> None:
        if not entries:
            return
        self.group(f"{title} ({len(entries)})", hint)
        width = min(max(len(e["name"]) for e in entries), 28)
        for entry in entries:
            tags = []
            if entry.get("user_only"):
                tags.append("user-invoked only")
            if entry.get("has_skill_md") is False:
                tags.append("no SKILL.md")
            self.row(f"{entry['name']:<{width}}", (self.dim(f"[{', '.join(tags)}] ") if tags else "") + first_sentence(entry.get("description")), key_width=width)
            if entry.get("broken"):
                self.warn(f"broken link → {tilde(entry['link_target'])}", indent=6 + width)
            elif "link_target" in entry:
                print(f"{' ' * (5 + width)}{self.dim('↳ ' + tilde(entry['link_target']))}")

    def plugins(self, report: dict) -> None:
        if not (report["installed"] or report["enabled_but_not_installed"] or report["marketplaces"]):
            return
        self.group(f"Plugins ({len(report['installed'])})")
        for plugin in report["installed"]:
            state = "" if plugin["enabled"] else self.dim("  disabled")
            self.row(plugin["name"], f"{plugin['version']}  {self.dim(plugin['scope'])}{state}", key_width=40)
            if not plugin["present"]:
                self.warn("plugin files missing from the plugin cache", indent=8)
        for name in report["enabled_but_not_installed"]:
            self.warn(f"{name} is enabled in settings.json but not installed")
        for m in report["marketplaces"]:
            src = m.get("repo") or m.get("url") or m.get("path") or m.get("source")
            ref = f"@{m['ref']}" if m.get("ref") else ""
            auto = self.dim("  auto-update") if m["auto_update"] else ""
            self.row(f"marketplace {m['name']}", f"{src}{ref}{auto}", key_width=40)

    def global_state(self, report: dict | None) -> None:
        if not report or not (report["preferences"] or report["mcp_servers"] or report["projects_with_customizations"]):
            return
        self.group("Global state", f"{tilde(report['path'])}  ·  {report['known_projects']} known projects")
        for key, value in report["preferences"].items():
            self.row(key, json.dumps(value), key_width=22, note=self.default_note(report["preference_defaults"].get(key), value))
        for server in report["mcp_servers"]:
            self.row("mcp server", mcp_line(server))
        for path, custom in report["projects_with_customizations"].items():
            self.row("project", f"{tilde(path)}  {self.dim(', '.join(f'{k}: {len(v)}' for k, v in custom.items()))}")
            if not Path(path).exists():
                self.warn("directory no longer exists", indent=8)

    def render(self, data: dict, implicit: bool) -> None:
        print(self.bold("Claude Code customizations") + self.dim("  ·  by location, in override order"))
        if implicit:
            print(self.dim("Implicit view: only what shapes a session without you invoking it. Run without --implicit for everything."))

        v = data["versions"]
        d = data["desktop"]
        self.section("Versions")
        if "cli" in v:
            self.row("CLI", f"{v['cli']['version']}  {self.dim(tilde(v['cli']['path']) + ', ' + v.get('install_method', '?') + ' install')}", count=False)
        else:
            self.warn("claude not found on PATH")
        bundled = d["bundled_claude_code_versions"] if d else []
        if bundled:
            self.row("Desktop", f"bundles Claude Code {', '.join(bundled)}", count=False)
            if desktop_lags_cli(data):
                self.warn("Desktop runs an older Claude Code than the CLI; behaviour can differ between the two", indent=4)
        self.row("Platform", v["platform"], count=False)

        u = data["user"]
        self.section("User scope", f"{tilde(u['config_dir'])}  ·  shared by the CLI and Claude Desktop")
        if not u["exists"]:
            self.none("config dir does not exist: this is a fresh install")
        self.settings("Settings", u["settings"], env=False)
        self.settings("Local settings", u["settings_local"])
        self.markdown("Instructions", u["claude_md"])
        self.markdown("Local instructions", u["claude_local_md"])
        if u["keybindings"] is not None:
            self.group("Keybindings", tilde(str(CONFIG_DIR / "keybindings.json")))
            self.items += 1
        self.entries("Skills", u["skills"], "loaded into every session; the model may invoke any not marked user-invoked only")
        self.entries("Commands", u["commands"])
        self.entries("Agents", u["agents"])
        self.entries("Rules", u["rules"])
        self.entries("Output styles", u["output_styles"])
        self.entries("Themes", u["themes"])
        self.entries("Workflows", u["workflows"])
        self.entries("Scheduled tasks", u["scheduled_tasks"], "run on their own schedule")
        if u["hook_scripts"]:
            self.group(f"Hook scripts ({len(u['hook_scripts'])})", tilde(str(CONFIG_DIR / "hooks")))
            for script in u["hook_scripts"]:
                self.row(script["name"], self.dim("registered") if script["registered"] else "", key_width=30)
                if not script["registered"]:
                    self.warn("present in hooks/ but no settings.json event runs it", indent=8)
        self.plugins(u["plugins"])
        self.global_state(u["global_state"])
        if u["unrecognized"]:
            self.group(f"Unrecognized ({len(u['unrecognized'])})", "neither a known customization nor known runtime state")
            self.warn("nothing in Claude Code owns these; cleanup candidates")
            for entry in u["unrecognized"]:
                self.row(entry["name"], self.dim(f"owned by {entry['owner']}") if entry["owner"] else "", key_width=48, count=False)

        self.section("Managed scope", "enterprise policy")
        if data["managed"]["files"]:
            for path, keys in data["managed"]["files"].items():
                self.row(path, ", ".join(keys) if isinstance(keys, list) else keys, key_width=len(path))
        else:
            self.none("none; searched " + ", ".join(data["managed"]["searched"]))

        self.section("Environment variables", "process, settings.json env block, shell rc files")
        if not data["environment"]:
            self.none("none")
        else:
            width = max(len(item["name"]) for item in data["environment"])
            value_width = min(max(len(str(item["value"])) for item in data["environment"]), 40)
            for item in data["environment"]:
                sources = ", ".join(item["sources"])
                self.row(item["name"], f"{item['value']!s:<{value_width}}  {self.dim(sources)}", key_width=width, note=self.default_note(item["default"], item["value"]))

        self.section("Claude Desktop", tilde(d["config_dir"]) if d else "")
        if d is None:
            self.none("Claude Desktop config dir not found")
        else:
            cfg = d.get("config") or {"mcp_servers": [], "preferences": {}, "keys": []}
            for server in cfg["mcp_servers"]:
                self.row("mcp server", mcp_line(server))
            for ext in d["extensions"]:
                self.row("extension", ext)
            if d["claude_code_env_vars_configured"]:
                self.row("env vars", "configured for Claude Code in Desktop " + self.dim("(encrypted, contents not readable)"))
            if cfg["preferences"]:
                self.group(f"Preferences ({len(cfg['preferences'])})")
                width = min(max(len(k) for k in cfg["preferences"]), 36)
                for key, value in cfg["preferences"].items():
                    self.row(key, json.dumps(value), key_width=width)
            other = [k for k in cfg["keys"] if k not in ("mcpServers", "preferences")]
            if other:
                self.row("other keys", ", ".join(other))
            if not (cfg["mcp_servers"] or d["extensions"] or d["claude_code_env_vars_configured"] or cfg["preferences"] or other):
                self.none("no Desktop-only customizations")

        pr = data["project"]
        self.section("Project scope", tilde(pr["path"]))
        if not pr["files"] and not pr["global_state_entry"]:
            self.none("none")
        for rel, report in pr["files"].items():
            if isinstance(report, list):
                if rel == ".mcp.json":
                    self.group(rel)
                    for server in report:
                        self.row("mcp server", mcp_line(server))
                elif rel == ".worktreeinclude":
                    self.row(rel, ", ".join(report), key_width=len(rel))
                else:
                    self.entries(rel, report)
            elif rel.endswith(".md"):
                self.markdown(rel, report)
            else:
                self.settings(rel, report)
        if pr["global_state_entry"]:
            self.group("Remembered for this project", tilde(GLOBAL_STATE.as_posix()))
            for key, value in pr["global_state_entry"].items():
                self.row(key, json.dumps(value), key_width=24)

        self.section("Summary")
        warnings = self.paint("33", f"{self.warnings} to look at (⚠)") if self.warnings else "nothing flagged"
        print(f"    {self.items} customizations  ·  {warnings}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of the text report")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="project directory to inspect (default: cwd)")
    parser.add_argument("--implicit", action="store_true", help="only what shapes a session without the user invoking it")
    parser.add_argument("--by-location", action="store_true", help="group by where each item lives instead of by what it does")
    args = parser.parse_args()
    data = inventory(args.project.resolve())
    if args.implicit:
        data = implicit_only(data)
    if args.json:
        json.dump(data, sys.stdout, indent=2, default=str)
        print()
    elif args.by_location:
        LocationReport().render(data, args.implicit)
    else:
        EffectReport(data, args.implicit).render()


if __name__ == "__main__":
    main()
