#!/usr/bin/env python3
"""Tests for inventory.py. Run: python3 test_inventory.py

Each test points HOME (and so the config dir, ~/.claude.json and the Desktop dir) at a throwaway
tree seeded with known customizations and runtime noise, then checks the JSON report.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INVENTORY = Path(__file__).resolve().parent / "inventory.py"


class InventoryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="cc-inv-"))
        self.config = self.home / ".claude"
        self.config.mkdir()
        self.project = self.home / "proj"
        self.project.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "ANTHROPIC_", "OTEL_"))}
        self.env["HOME"] = str(self.home)

    def run_inventory(self, *args: str) -> dict:
        proc = subprocess.run(
            [sys.executable, str(INVENTORY), "--json", "--project", str(self.project), *args],
            env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_fresh_install_reports_nothing(self) -> None:
        data = self.run_inventory()
        user = data["user"]
        self.assertIsNone(user["settings"])
        self.assertIsNone(user["claude_md"])
        self.assertEqual(user["skills"], [])
        self.assertEqual(user["plugins"]["installed"], [])
        self.assertEqual(user["unrecognized"], [])
        self.assertEqual(data["environment"], [])
        self.assertIsNone(data["desktop"])
        self.assertEqual(data["project"]["files"], {})

    def test_user_scope_customizations(self) -> None:
        (self.config / "settings.json").write_text(json.dumps({
            "model": "opus",
            "env": {"OTEL_LOGS_EXPORTER": "otlp", "ANTHROPIC_API_KEY": "sk-ant-secret"},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/guard.py"}]}]},
            "enabledPlugins": {"a@m": True, "ghost@m": True},
        }))
        (self.config / "CLAUDE.md").write_text("<!-- bundle:begin v1 (managed) -->\n# Rule\n<!-- bundle:end -->\n")
        skills = self.config / "skills"
        (skills / "mine").mkdir(parents=True)
        (skills / "mine" / "SKILL.md").write_text("---\nname: mine\ndescription: does things\n---\n")
        try:
            (skills / "dangling").symlink_to(self.home / "gone")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not supported here")
        hooks = self.config / "hooks"
        hooks.mkdir()
        (hooks / "guard.py").write_text("")
        (hooks / "orphan.py").write_text("")
        plugins = self.config / "plugins"
        plugins.mkdir()
        (plugins / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {
            "a@m": [{"scope": "user", "version": "1.0", "installPath": str(self.home / "missing")}]}}))
        (plugins / "known_marketplaces.json").write_text(json.dumps({"m": {"source": {"source": "github", "repo": "o/r"}}}))
        (self.config / "history.jsonl").write_text("")
        (self.config / "leftover.bak").write_text("")
        (self.home / ".claude.json").write_text(json.dumps({
            "theme": "dark", "numStartups": 9, "mcpServers": {"srv": {"command": "npx", "args": ["x"], "env": {"TOKEN": "t"}},
                                                             "remote": {"type": "http", "url": "https://me:s3cret@mcp.example/sse"}},
            "projects": {str(self.project): {"allowedTools": ["Bash(ls:*)"], "lastCost": 1}, "/other": {"allowedTools": []}},
        }))

        user = self.run_inventory()["user"]
        self.assertEqual(user["settings"]["values"], {"model": "opus"})
        self.assertEqual(user["settings"]["env"]["ANTHROPIC_API_KEY"], "<redacted>")
        self.assertEqual(user["settings"]["hooks"], {"PreToolUse": ["[Bash] python3 ~/.claude/hooks/guard.py"]})
        self.assertEqual(user["claude_md"]["managed_blocks"], ["bundle v1"])
        by_name = {s["name"]: s for s in user["skills"]}
        self.assertEqual(by_name["mine"]["description"], "does things")
        self.assertTrue(by_name["dangling"]["broken"])
        self.assertEqual({h["name"]: h["registered"] for h in user["hook_scripts"]}, {"guard.py": True, "orphan.py": False})
        plugin = user["plugins"]["installed"][0]
        self.assertEqual((plugin["enabled"], plugin["present"]), (True, False))
        self.assertEqual(user["plugins"]["enabled_but_not_installed"], ["ghost@m"])
        self.assertEqual(user["plugins"]["marketplaces"][0]["repo"], "o/r")
        self.assertEqual(user["unrecognized"], [{"name": "leftover.bak", "backup": False, "owner": None}])
        state = user["global_state"]
        self.assertEqual(state["preferences"], {"theme": "dark"})
        self.assertEqual(state["mcp_servers"], [
            {"name": "remote", "type": "http", "url": "https://<redacted>@mcp.example/sse"},
            {"name": "srv", "command": "npx", "args": ["x"], "env_keys": ["TOKEN"]},
        ])
        self.assertEqual(list(state["projects_with_customizations"]), [str(self.project)])

    def test_environment_sources(self) -> None:
        (self.config / "settings.json").write_text(json.dumps({"env": {"OTEL_LOGS_EXPORTER": "otlp"}}))
        (self.home / ".zshrc").write_text("alias ll='ls'\nexport ANTHROPIC_MODEL=opus\nMAX_THINKING_TOKENS=1\n")
        self.env["DISABLE_TELEMETRY"] = "1"
        self.env["HTTPS_PROXY"] = "http://corp:pa55@proxy.example:8080"
        self.env["CLAUDECODE"] = "1"

        env = {item["name"]: item for item in self.run_inventory()["environment"]}
        self.assertEqual(set(env), {"OTEL_LOGS_EXPORTER", "ANTHROPIC_MODEL", "MAX_THINKING_TOKENS", "DISABLE_TELEMETRY", "HTTPS_PROXY"})
        self.assertEqual(env["HTTPS_PROXY"]["value"], "http://<redacted>@proxy.example:8080")
        self.assertEqual((env["OTEL_LOGS_EXPORTER"]["value"], env["OTEL_LOGS_EXPORTER"]["sources"]), ("otlp", ["settings.json"]))
        self.assertEqual(env["ANTHROPIC_MODEL"]["sources"], ["~/.zshrc:2"])
        self.assertEqual(env["DISABLE_TELEMETRY"]["sources"], ["process"])

    def test_documented_defaults(self) -> None:
        (self.config / "settings.json").write_text(json.dumps({"cleanupPeriodDays": 7, "tui": "fullscreen", "env": {"BASH_MAX_OUTPUT_LENGTH": "1", "MY_UNKNOWN": "x"}}))
        self.env["OTEL_METRIC_EXPORT_INTERVAL"] = "60000"
        (self.home / ".claude.json").write_text(json.dumps({"autoConnectIde": True}))

        data = self.run_inventory()
        self.assertEqual(data["user"]["settings"]["defaults"], {"cleanupPeriodDays": "30"})
        self.assertEqual(data["user"]["global_state"]["preference_defaults"], {"autoConnectIde": "false"})
        env = {item["name"]: item["default"] for item in data["environment"]}
        self.assertEqual(env, {"BASH_MAX_OUTPUT_LENGTH": "30000", "MY_UNKNOWN": "unset", "OTEL_METRIC_EXPORT_INTERVAL": "60000"})

        text = subprocess.run([sys.executable, str(INVENTORY), "--project", str(self.project)], env=self.env, capture_output=True, text=True).stdout
        self.assertRegex(text, r"cleanupPeriodDays 7\s+~/.claude/settings.json\s+default: 30")
        self.assertRegex(text, r"OTEL_METRIC_EXPORT_INTERVAL=60000\s+process\s+\(= default\)")

    def test_project_scope(self) -> None:
        (self.project / "CLAUDE.md").write_text("# Project\n@AGENTS.md\n")
        (self.project / ".mcp.json").write_text(json.dumps({"mcpServers": {"db": {"type": "http", "url": "http://x"}}}))
        dot = self.project / ".claude"
        (dot / "commands").mkdir(parents=True)
        (dot / "commands" / "deploy.md").write_text("---\ndescription: ship it\n---\n")
        (dot / "settings.local.json").write_text(json.dumps({"permissions": {"allow": ["Bash(make:*)"]}}))

        files = self.run_inventory()["project"]["files"]
        self.assertEqual(files["CLAUDE.md"]["includes"], ["AGENTS.md"])
        self.assertEqual(files[".mcp.json"], [{"name": "db", "type": "http", "url": "http://x"}])
        self.assertEqual(files[".claude/commands"][0]["description"], "ship it")
        self.assertEqual(files[".claude/settings.local.json"]["permissions"], {"allow": ["Bash(make:*)"]})

    @unittest.skipUnless(sys.platform == "darwin", "Desktop layout is per-OS; only the macOS path is exercised here")
    def test_desktop_scope(self) -> None:
        desktop = self.home / "Library/Application Support/Claude"
        (desktop / "Claude Extensions" / "ext.mcpb").mkdir(parents=True)
        (desktop / "claude-code" / "2.1.0").mkdir(parents=True)
        (desktop / "claude_desktop_config.json").write_text(json.dumps({
            "mcpServers": {"fs": {"command": "npx", "args": ["fs"]}}, "preferences": {"apiKey": "k", "sidebarMode": "x"},
        }))
        (desktop / "ccd-environment-config.json").write_text("{}")

        d = self.run_inventory()["desktop"]
        self.assertEqual(d["config"]["mcp_servers"], [{"name": "fs", "command": "npx", "args": ["fs"]}])
        self.assertEqual(d["config"]["preferences"], {"apiKey": "<redacted>", "sidebarMode": "x"})
        self.assertEqual(d["extensions"], ["ext.mcpb"])
        self.assertEqual(d["bundled_claude_code_versions"], ["2.1.0"])
        self.assertTrue(d["claude_code_env_vars_configured"])

    def test_implicit_keeps_only_what_acts_on_a_session(self) -> None:
        (self.config / "settings.json").write_text(json.dumps({
            "model": "opus", "tui": "fullscreen", "extraKnownMarketplaces": {"m": {}},
            "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/guard.py"}]}]},
            "enabledPlugins": {"a@m": True, "off@m": False},
        }))
        skills = self.config / "skills"
        for name, flag in (("auto", ""), ("manual", "disable-model-invocation: true\n")):
            (skills / name).mkdir(parents=True)
            (skills / name / "SKILL.md").write_text(f"---\nname: {name}\n{flag}description: d\n---\n")
        hooks = self.config / "hooks"
        hooks.mkdir()
        (hooks / "guard.py").write_text("")
        (hooks / "orphan.py").write_text("")
        (self.config / "keybindings.json").write_text("{}")
        (self.config / "leftover.bak").write_text("")
        (self.config / "plugins").mkdir()
        (self.config / "plugins" / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {
            "a@m": [{"scope": "user", "version": "1", "installPath": str(self.config)}],
            "off@m": [{"scope": "user", "version": "1", "installPath": str(self.config)}]}}))
        (self.home / ".claude.json").write_text(json.dumps({"theme": "dark", "mcpServers": {"srv": {"command": "x"}}}))

        full = self.run_inventory()["user"]
        self.assertTrue({s["name"]: s.get("user_only") for s in full["skills"]}["manual"])

        user = self.run_inventory("--implicit")["user"]
        self.assertEqual(user["settings"]["values"], {"model": "opus"})
        self.assertNotIn("marketplaces", user["settings"])
        self.assertEqual(list(user["settings"]["hooks"]), ["Stop"])
        self.assertEqual([s["name"] for s in user["skills"]], ["auto"])
        self.assertEqual([h["name"] for h in user["hook_scripts"]], ["guard.py"])
        self.assertEqual([p["name"] for p in user["plugins"]["installed"]], ["a@m"])
        self.assertEqual(user["plugins"]["marketplaces"], [])
        self.assertIsNone(user["keybindings"])
        self.assertEqual(user["unrecognized"], [])
        self.assertEqual(user["global_state"]["preferences"], {})
        self.assertEqual([m["name"] for m in user["global_state"]["mcp_servers"]], ["srv"])

    def test_leftover_attribution(self) -> None:
        (self.config / "CLAUDE.md").write_text("<!-- practices:begin v1 -->\n# x\n<!-- practices:end -->\n")
        (self.config / "hooks").mkdir()
        (self.config / "hooks" / "vibe_diary_hook.py").write_text("")
        for name in ("practices.json", "vibe-diary.log", "shims", "settings.json.old.bak"):
            (self.config / name).write_text("")

        owners = {e["name"]: (e["owner"], e["backup"]) for e in self.run_inventory()["user"]["unrecognized"]}
        self.assertEqual(owners, {
            "practices.json": ("the practices bundle", False),
            "vibe-diary.log": ("hook script vibe_diary_hook.py", False),
            "shims": (None, False),
            "settings.json.old.bak": (None, True),
        })

    def text(self, *args: str) -> str:
        proc = subprocess.run([sys.executable, str(INVENTORY), "--project", str(self.project), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def test_text_report_layouts(self) -> None:
        (self.config / "settings.json").write_text(json.dumps({"model": "opus", "tui": "fullscreen", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}}))
        (self.config / "shims").mkdir()

        effect = self.text()
        self.assertEqual([l[2:].split("  ")[0] for l in effect.splitlines() if l.startswith("▌")],
                         ["Instructions", "Behaviour", "Automation", "Tools", "Interface", "Leftovers", "Summary"])
        self.assertRegex(effect, r'model\s+"opus"')
        self.assertRegex(effect, r"hook\s+Stop\s+echo hi")
        self.assertIn("⚠ shims/", effect)
        self.assertIn("2 session-shaping items  ·  1 interface-only  ·  1 leftovers", effect)

        implicit = self.text("--implicit")
        self.assertEqual([l[2:].split("  ")[0] for l in implicit.splitlines() if l.startswith("▌")],
                         ["Instructions", "Behaviour", "Automation", "Tools", "Summary"])
        self.assertNotIn("fullscreen", implicit)

        location = self.text("--by-location")
        self.assertIn("▌ User scope", location)
        self.assertIn("▌ Claude Desktop", location)
        self.assertRegex(location, r'model\s+"opus"')


if __name__ == "__main__":
    unittest.main()
