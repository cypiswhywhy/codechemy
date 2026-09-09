#!/usr/bin/env python3
"""Tests for install.py. Run: python3 test_install.py

Each test installs into a throwaway CLAUDE_CONFIG_DIR seeded with a pre-existing CLAUDE.md and
settings.json, then checks the bundle merged in without disturbing them and comes out clean.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
INSTALLER = HERE / "install.py"
sys.path.insert(0, str(HERE))
import install  # noqa: E402

OTHER_HOOK = {"hooks": [{"type": "command", "command": "echo other"}]}


class InstallerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Path(tempfile.mkdtemp(prefix="ep-cfg-"))
        self.env = {**os.environ, "CLAUDE_CONFIG_DIR": str(self.config), "ENGINEERING_PRACTICES_NO_SELFTEST": "1"}

    def run_installer(self, *args: str) -> str:
        proc = subprocess.run([sys.executable, str(INSTALLER), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def files(self) -> dict:
        return {p: p.read_bytes() for p in self.config.rglob("*") if p.is_file() and ".bak" not in p.name}

    def test_install_merges_and_is_idempotent(self) -> None:
        (self.config / "CLAUDE.md").write_text("# Mine\n\nKeep this.\n")
        (self.config / "settings.json").write_text(json.dumps({
            "permissions": {"allow": ["Bash(ls)"]},
            "hooks": {"Stop": [OTHER_HOOK]},
        }))
        self.run_installer()

        text = (self.config / "CLAUDE.md").read_text()
        self.assertTrue(text.startswith("# Mine\n\nKeep this.\n\n<!-- engineering-practices:begin"))
        self.assertTrue(text.rstrip().endswith("<!-- engineering-practices:end -->"))
        for practice in install.PRACTICES:
            self.assertIn(practice.read_text().strip().splitlines()[0], text)

        settings = json.loads((self.config / "settings.json").read_text())
        self.assertEqual(settings["permissions"], {"allow": ["Bash(ls)"]})
        stop_cmds = [h["command"] for g in settings["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(stop_cmds[0], "echo other")
        self.assertEqual(len([c for c in stop_cmds if "leave_it_smaller.py" in c]), 1)
        self.assertEqual(len(settings["hooks"]["SessionStart"]), 1)
        self.assertTrue((self.config / "hooks" / "leave_it_smaller.py").exists())
        for skill in install.SKILLS:
            target = self.config / "skills" / skill.name
            self.assertFalse(target.is_symlink())
            self.assertEqual((target / "SKILL.md").read_text(), (skill / "SKILL.md").read_text())
        state = json.loads((self.config / "engineering-practices.json").read_text())
        self.assertEqual(state["version"], install.VERSION)
        self.assertEqual(state["skills"], [s.name for s in install.SKILLS])
        self.assertIn(f"engineering-practices:begin v{install.VERSION}", text)

        snapshot = self.files()
        self.run_installer()
        self.assertEqual(self.files(), snapshot)

    def test_reinstall_replaces_block_and_hooks_in_place(self) -> None:
        self.run_installer()
        claude_md = self.config / "CLAUDE.md"
        claude_md.write_text(claude_md.read_text().replace("Leave the code smaller", "STALE"))
        settings_path = self.config / "settings.json"
        settings = json.loads(settings_path.read_text())
        settings["hooks"]["Stop"][0]["hooks"][0]["command"] = 'python3 "/old/path/hooks/leave_it_smaller.py" stop'
        settings_path.write_text(json.dumps(settings))
        self.run_installer()
        self.assertNotIn("STALE", claude_md.read_text())
        self.assertEqual(claude_md.read_text().count("engineering-practices:begin"), 1)
        stop_cmds = [h["command"] for g in json.loads(settings_path.read_text())["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(len(stop_cmds), 1)
        self.assertIn(str(self.config / "hooks"), stop_cmds[0])

    def test_uninstall_restores_neighbours(self) -> None:
        (self.config / "CLAUDE.md").write_text("# Mine\n")
        (self.config / "settings.json").write_text(json.dumps({"hooks": {"Stop": [OTHER_HOOK]}}))
        self.run_installer()
        self.run_installer("--uninstall")
        self.assertEqual((self.config / "CLAUDE.md").read_text(), "# Mine\n")
        self.assertEqual(json.loads((self.config / "settings.json").read_text())["hooks"], {"Stop": [OTHER_HOOK]})
        self.assertFalse((self.config / "hooks" / "leave_it_smaller.py").exists())
        self.assertEqual(list((self.config / "skills").iterdir()), [])
        self.assertFalse((self.config / "engineering-practices.json").exists())

    def test_uninstall_on_empty_config_leaves_nothing_of_ours(self) -> None:
        self.run_installer()
        self.run_installer("--uninstall")
        self.assertFalse((self.config / "CLAUDE.md").exists())
        self.assertNotIn("hooks", json.loads((self.config / "settings.json").read_text()))

    def test_foreign_skill_dir_is_never_replaced_or_removed(self) -> None:
        theirs = self.config / "skills" / "maintenance-toolbox" / "SKILL.md"
        theirs.parent.mkdir(parents=True)
        theirs.write_text("theirs")
        out = self.run_installer()
        self.assertIn("skipped", out)
        self.assertEqual(theirs.read_text(), "theirs")
        self.assertNotIn("maintenance-toolbox", json.loads((self.config / "engineering-practices.json").read_text())["skills"])
        self.run_installer("--uninstall")
        self.assertEqual(theirs.read_text(), "theirs")

    def test_foreign_symlinked_skill_is_left_alone(self) -> None:
        link = self.config / "skills" / "apply-increment"
        link.parent.mkdir()
        link.symlink_to(install.SKILLS[0])
        self.assertIn("skipped", self.run_installer())
        self.assertTrue(link.is_symlink())
        self.run_installer("--uninstall")
        self.assertTrue(link.is_symlink())

    def test_installed_copy_is_refreshed_on_reinstall_and_git_pull_changes_nothing(self) -> None:
        self.run_installer()
        skill = self.config / "skills" / "maintenance-toolbox" / "SKILL.md"
        skill.write_text("stale")
        self.assertEqual(skill.read_text(), "stale")  # nothing outside the installer touches it
        self.run_installer()
        self.assertNotEqual(skill.read_text(), "stale")

    def test_status_reports_installed_and_available(self) -> None:
        self.assertIn("not installed", self.run_installer("--status"))
        self.run_installer()
        out = self.run_installer("--status")
        self.assertIn(f"installed  v{install.VERSION}", out)
        self.assertIn(f"available  v{install.VERSION}", out)
        self.assertNotIn("run: make", out)
        state_file = self.config / "engineering-practices.json"
        state = json.loads(state_file.read_text()); state["version"] = "0.0.1"; state_file.write_text(json.dumps(state))
        self.assertIn("run: make install-engineering-practices", self.run_installer("--status"))

    def test_version_file_is_semver(self) -> None:
        major, minor, patch = install.VERSION.split(".")
        self.assertTrue(all(part.isdigit() for part in (major, minor, patch)), install.VERSION)

    def test_strip_block_keeps_surrounding_text(self) -> None:
        text = "before\n\n<!-- engineering-practices:begin x -->\nbody\n<!-- engineering-practices:end -->\n\nafter\n"
        self.assertEqual(install.strip_block(text), "before\n\nafter\n")
        self.assertEqual(install.strip_block("<!-- engineering-practices:begin -->\nb\n<!-- engineering-practices:end -->\n"), "")


if __name__ == "__main__":
    unittest.main()
