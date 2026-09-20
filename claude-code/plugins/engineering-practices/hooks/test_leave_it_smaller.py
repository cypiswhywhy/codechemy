#!/usr/bin/env python3
"""Tests for leave_it_smaller.py. Run: python3 test_hook.py

Each test builds a throwaway git repository and a throwaway CLAUDE_CONFIG_DIR, then drives
the hook exactly as Claude Code does: a JSON payload on stdin, a subcommand argument.
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
HOOK = HERE / "leave_it_smaller.py"
sys.path.insert(0, str(HERE))
import leave_it_smaller  # noqa: E402

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": "/dev/null",
}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=GIT_ENV, check=True, capture_output=True, text=True).stdout


def lines(n: int, prefix: str = "line") -> str:
    return "".join(f"{prefix} {i}\n" for i in range(n))


class HookCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="lis-"))
        self.config = self.tmp / "config"
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "a.py").write_text(lines(10))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "seed")

    def run_hook(self, command: str, **payload) -> dict | str:
        data = {"session_id": "s1", "cwd": str(self.repo), **payload}
        env = {**GIT_ENV, "CLAUDE_CONFIG_DIR": str(self.config)}
        for k in list(env):
            if k.startswith("LEAVE_IT_SMALLER_"):
                del env[k]
        proc = subprocess.run(
            [sys.executable, str(HOOK), command], input=json.dumps(data), env=env,
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.strip()
        if not out:
            return {}
        try:
            return json.loads(out)
        except ValueError:
            return out

    # ----- stop -----

    def test_outside_a_repository_is_silent(self) -> None:
        self.assertEqual(self.run_hook("stop", cwd=str(self.tmp)), {})

    def test_clean_tree_is_silent(self) -> None:
        self.assertEqual(self.run_hook("stop"), {})

    def test_add_only_growth_blocks_then_dedupes_then_caps(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        first = self.run_hook("stop")
        self.assertEqual(first.get("decision"), "block")
        self.assertIn("+50 / -0", first["reason"])
        self.assertIn("added +50 and removed only -0", first["reason"])
        # Same diff again: already nudged on this exact shape, nothing new to say.
        self.assertEqual(self.run_hook("stop"), {})
        # Still add-only after more edits: second (and last) nudge.
        (self.repo / "a.py").write_text(lines(10) + lines(80, "new"))
        self.assertEqual(self.run_hook("stop").get("decision"), "block")
        # Cap reached: the smell is still reported, but the stop is no longer blocked.
        (self.repo / "a.py").write_text(lines(10) + lines(90, "new"))
        third = self.run_hook("stop")
        self.assertNotIn("decision", third)
        self.assertIn("add-only", third["systemMessage"])

    def test_stop_hook_active_never_blocks(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        out = self.run_hook("stop", stop_hook_active=True)
        self.assertNotIn("decision", out)
        self.assertIn("+50 / -0", out["systemMessage"])

    def test_balanced_change_reports_without_blocking(self) -> None:
        (self.repo / "a.py").write_text(lines(2) + lines(45, "other"))  # -8 / +45
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)
        self.assertIn("+45 / -8", out["systemMessage"])
        self.assertNotIn("add-only", out["systemMessage"])

    def test_small_additions_are_not_growth(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(20, "new"))
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)
        self.assertIn("+20 / -0", out["systemMessage"])

    def test_a_new_file_alone_is_add_only_and_blocks(self) -> None:
        (self.repo / "b.py").write_text(lines(200))  # untracked
        out = self.run_hook("stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("(0 existing: +0 / -0; 1 new)", out["reason"])
        self.assertIn("already has", out["reason"])

    def test_deletions_elsewhere_excuse_a_new_file(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(100, "grow"))
        git(self.repo, "commit", "-qam", "grow")
        (self.repo / "b.py").write_text(lines(200))
        (self.repo / "a.py").write_text(lines(10))  # -100
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)
        self.assertNotIn("add-only", out["systemMessage"])
        self.assertIn("+200 / -100", out["systemMessage"])

    def test_large_change_nudges_once(self) -> None:
        (self.repo / "b.py").write_text(lines(500))
        first = self.run_hook("stop")
        self.assertEqual(first.get("decision"), "block")
        self.assertIn("already 500 lines", first["reason"])
        self.assertIn("landing points you named", first["reason"])
        # Still large, but the seam question is asked only once per session.
        (self.repo / "b.py").write_text(lines(520))
        second = self.run_hook("stop")
        self.assertNotIn("landing points you named", second["reason"])
        # Nudge cap reached: the shape is reported, not blocked.
        (self.repo / "b.py").write_text(lines(540))
        third = self.run_hook("stop")
        self.assertNotIn("decision", third)
        self.assertIn("large change", third["systemMessage"])

    def test_feature_branch_is_measured_against_main(self) -> None:
        git(self.repo, "checkout", "-qb", "feature")
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        git(self.repo, "commit", "-qam", "grow")  # clean tree, committed growth
        out = self.run_hook("stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("+50 / -0", out["reason"])

    def test_main_with_upstream_measures_unpushed_work(self) -> None:
        remote = self.tmp / "remote.git"
        git(self.repo, "init", "-q", "--bare", str(remote))
        git(self.repo, "remote", "add", "origin", str(remote))
        git(self.repo, "push", "-qu", "origin", "main")
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        git(self.repo, "commit", "-qam", "grow")
        self.assertEqual(self.run_hook("stop").get("decision"), "block")

    def test_binary_and_deleted_files_are_handled(self) -> None:
        (self.repo / "img.bin").write_bytes(b"\0\1\2" * 100)
        (self.repo / "a.py").unlink()
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)
        self.assertIn("+0 / -10 across 1 file(s)", out["systemMessage"])

    def test_disable_env_is_silent(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        env = {**GIT_ENV, "CLAUDE_CONFIG_DIR": str(self.config), "LEAVE_IT_SMALLER_DISABLE": "1"}
        proc = subprocess.run(
            [sys.executable, str(HOOK), "stop"], input=json.dumps({"cwd": str(self.repo)}),
            env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))

    def test_rename_target_parsing(self) -> None:
        self.assertEqual(leave_it_smaller.rename_target("old.py => new.py"), "new.py")
        self.assertEqual(leave_it_smaller.rename_target("src/{old => new}/x.py"), "src/new/x.py")
        self.assertEqual(leave_it_smaller.rename_target("plain.py"), "plain.py")

    def test_renamed_file_counts_as_existing(self) -> None:
        # Similarity must stay above git's 50% rename threshold, or it reads as delete + add.
        (self.repo / "a.py").write_text(lines(100))
        git(self.repo, "commit", "-qam", "bigger")
        git(self.repo, "mv", "a.py", "renamed.py")
        (self.repo / "renamed.py").write_text(lines(100) + lines(50, "new"))
        out = self.run_hook("stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("(1 existing: +50 / -0; 0 new)", out["reason"])

    # ----- session-start -----

    def test_session_start_hints_without_toolbox(self) -> None:
        self.assertIn("/maintenance-toolbox", self.run_hook("session-start"))

    def test_session_start_silent_with_toolbox_or_opt_out(self) -> None:
        (self.repo / "CLAUDE.md").write_text("# x\n\n## Maintenance toolbox\n- Tests: `pytest`\n")
        self.assertEqual(self.run_hook("session-start"), {})
        (self.repo / "CLAUDE.md").write_text("<!-- maintenance-toolbox: none -->\n")
        self.assertEqual(self.run_hook("session-start"), {})

    def test_session_start_reads_dot_claude_dir(self) -> None:
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "CLAUDE.md").write_text("## Maintenance toolbox\n")
        self.assertEqual(self.run_hook("session-start"), {})

    def test_unknown_subcommand_exits_2(self) -> None:
        proc = subprocess.run([sys.executable, str(HOOK), "bogus"], input="{}", capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
