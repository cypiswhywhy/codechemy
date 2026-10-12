#!/usr/bin/env python3
"""Tests for leave_it_smaller.py. Run: python3 test_leave_it_smaller.py

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

    def test_add_only_growth_is_nudged_once_per_session(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        first = self.run_hook("stop")
        self.assertEqual(first.get("decision"), "block")
        self.assertIn("+50 / -0", first["reason"])
        self.assertIn("added +50 and removed only -0", first["reason"])
        # Same diff again: already nudged on this exact shape, nothing new to say.
        self.assertEqual(self.run_hook("stop"), {})
        # Still add-only after more edits: the smell is reported, the questions are not re-asked.
        (self.repo / "a.py").write_text(lines(10) + lines(80, "new"))
        second = self.run_hook("stop")
        self.assertNotIn("decision", second)
        self.assertIn("add-only", second["systemMessage"])

    def test_work_left_from_before_the_session_is_silent_until_the_session_changes_it(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(500, "earlier"))
        self.run_hook("session-start")
        self.assertEqual(self.run_hook("stop"), {})
        (self.repo / "a.py").write_text(lines(10) + lines(550, "earlier"))
        self.assertEqual(self.run_hook("stop").get("decision"), "block")

    def test_a_resumed_or_compacted_session_keeps_its_first_baseline(self) -> None:
        self.run_hook("session-start")
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        self.run_hook("session-start")
        self.assertEqual(self.run_hook("stop").get("decision"), "block")

    def test_add_only_asks_for_one_line_when_nothing_can_go(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        reason = self.run_hook("stop")["reason"]
        self.assertIn("dead code", reason)
        self.assertIn("If nothing can go, say so in one line.", reason)

    def test_a_docs_only_addition_is_asked_only_about_repetition_and_replaced_text(self) -> None:
        (self.repo / "README.md").write_text(lines(60, "prose"))
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "spec.md").write_text(lines(30, "requirement"))
        reason = self.run_hook("stop")["reason"]
        self.assertIn("repeat something the repository already has", reason)
        self.assertIn("older section, page, spec or task", reason)
        self.assertNotIn("dead code", reason)
        self.assertIn("If nothing can go, say so in one line.", reason)

    def test_a_session_on_a_branch_with_earlier_work_is_measured_on_its_own_lines(self) -> None:
        git(self.repo, "checkout", "-qb", "feature")
        (self.repo / "a.py").write_text(lines(10) + lines(300, "earlier"))
        git(self.repo, "commit", "-qam", "earlier session")
        self.run_hook("session-start")
        (self.repo / "a.py").write_text(lines(10) + lines(310, "earlier"))
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)
        self.assertIn("+10 / -0", out["systemMessage"])

    def test_undoing_earlier_work_counts_as_removed(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(500, "earlier"))
        self.run_hook("session-start")
        git(self.repo, "checkout", "a.py")
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)
        self.assertIn("+0 / -500", out["systemMessage"])

    def test_pushing_the_default_branch_starts_a_new_baseline(self) -> None:
        remote = self.tmp / "remote.git"
        git(self.repo, "init", "-q", "--bare", str(remote))
        git(self.repo, "remote", "add", "origin", str(remote))
        git(self.repo, "push", "-qu", "origin", "main")
        (self.repo / "a.py").write_text(lines(10) + lines(100, "earlier"))
        git(self.repo, "commit", "-qam", "unpushed before the session")
        self.run_hook("session-start")
        git(self.repo, "push", "-q")
        self.assertEqual(self.run_hook("stop"), {})
        (self.repo / "a.py").write_text(lines(10) + lines(150, "earlier"))
        out = self.run_hook("stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("+50 / -0", out["reason"])

    def test_stop_hook_active_never_blocks(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        out = self.run_hook("stop", stop_hook_active=True)
        self.assertNotIn("decision", out)
        self.assertIn("+50 / -0", out["systemMessage"])

    def test_balanced_change_reports_without_blocking(self) -> None:
        (self.repo / "a.py").write_text(lines(2) + lines(45, "other"))  # -8 / +45
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)
        self.assertTrue(out["systemMessage"].startswith("leave-it-smaller: this session +45 / -8"))
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

    def test_a_large_change_is_flagged_without_blocking(self) -> None:
        (self.repo / "b.py").write_text(lines(100))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "b")
        (self.repo / "b.py").write_text(lines(400, "other"))  # -100 / +400: large, not add-only
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)
        self.assertIn("large change", out["systemMessage"])

    def test_blocks_stop_at_the_cap_even_when_a_new_check_fails(self) -> None:
        self.seed_tests()
        (self.repo / "a.py").write_text(lines(2) + lines(45, "other"))
        self.assertIn("no test changed with it", self.run_hook("stop")["reason"])
        (self.repo / "a.py").write_text(lines(2) + lines(95, "other"))
        self.assertIn("removed only", self.run_hook("stop")["reason"])
        (self.repo / "c.py").write_text(lines(30, "# why"))
        third = self.run_hook("stop")
        self.assertNotIn("decision", third)
        self.assertIn("systemMessage", third)

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

    def test_project_opt_out_marker_is_silent(self) -> None:
        (self.repo / "CLAUDE.md").write_text("<!-- engineering-practices: off -->\n")
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        self.assertEqual(self.run_hook("stop"), {})
        self.assertEqual(self.run_hook("session-start"), {})

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

    # ----- the test-touch check -----

    def seed_tests(self) -> None:
        """A committed test file, so the repository counts as having a harness."""
        (self.repo / "tests").mkdir(exist_ok=True)
        (self.repo / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "tests")

    def test_source_change_without_a_test_change_is_nudged(self) -> None:
        self.seed_tests()
        (self.repo / "a.py").write_text(lines(2) + lines(45, "other"))  # balanced, not add-only
        out = self.run_hook("stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("no test changed with it", out["reason"])

    def test_changing_a_test_too_satisfies_the_check(self) -> None:
        self.seed_tests()
        (self.repo / "a.py").write_text(lines(2) + lines(45, "other"))
        (self.repo / "tests" / "test_a.py").write_text("def test_a():\n    assert 1 == 1\n")
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)

    def test_repository_without_a_harness_is_not_nudged(self) -> None:
        (self.repo / "a.py").write_text(lines(2) + lines(45, "other"))
        out = self.run_hook("stop")
        self.assertNotIn("decision", out)

    def test_docs_and_config_only_changes_are_not_nudged(self) -> None:
        self.seed_tests()
        (self.repo / "README.md").write_text(lines(60, "prose "))
        (self.repo / "conf.yaml").write_text(lines(60, "k"))
        out = self.run_hook("stop")
        self.assertNotIn("no test changed with it", json.dumps(out))

    def test_the_test_nudge_is_asked_once_per_session(self) -> None:
        self.seed_tests()
        (self.repo / "a.py").write_text(lines(2) + lines(45, "other"))
        self.assertIn("no test changed with it", self.run_hook("stop")["reason"])
        (self.repo / "a.py").write_text(lines(2) + lines(60, "other"))
        self.assertNotIn("no test changed with it", json.dumps(self.run_hook("stop")))

    # ----- the prose-density check -----

    def commented(self, code: int, prose: int) -> str:
        return "".join(f"# why {i}\n" for i in range(prose)) + "".join(f"x{i} = {i}\n" for i in range(code))

    def test_a_file_that_grew_mostly_by_comments_is_nudged_once(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + self.commented(code=10, prose=20))
        out = self.run_hook("stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("a.py: +30 lines, 20 of them comments or docstrings (67%)", out["reason"])
        (self.repo / "a.py").write_text(lines(10) + self.commented(code=10, prose=40))
        self.assertNotIn("comments or docstrings", json.dumps(self.run_hook("stop")))

    def test_a_change_matching_the_files_own_density_passes(self) -> None:
        (self.repo / "b.py").write_text(self.commented(code=10, prose=10))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "half prose already")
        (self.repo / "b.py").write_text(self.commented(code=20, prose=22))
        self.assertNotIn("comments or docstrings", json.dumps(self.run_hook("stop")))

    def test_a_new_file_that_is_mostly_docstring_is_nudged(self) -> None:
        doc = "".join(f"    paragraph {i}\n" for i in range(20))
        (self.repo / "c.py").write_text(f'def f():\n    """Contract.\n\n{doc}    """\n    return 1\n')
        out = self.run_hook("stop")
        self.assertIn("c.py: +25 lines, 23 of them comments or docstrings", out["reason"])

    def test_comments_written_before_the_session_are_not_its_prose(self) -> None:
        (self.repo / "c.py").write_text(self.commented(code=10, prose=0))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "c")
        (self.repo / "c.py").write_text(self.commented(code=10, prose=30))
        self.run_hook("session-start")
        (self.repo / "c.py").write_text(self.commented(code=35, prose=30))
        self.assertNotIn("comments or docstrings", json.dumps(self.run_hook("stop")))

    def test_small_growth_is_not_measured_for_prose(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + self.commented(code=0, prose=15))
        self.assertNotIn("comments or docstrings", json.dumps(self.run_hook("stop")))

    # ----- the transcript -----

    def transcript(self, *entries: str | dict) -> str:
        """A transcript file; a str entry is an assistant message with that text."""
        path = self.tmp / "transcript.jsonl"
        path.write_text("".join(
            json.dumps(
                {"type": "assistant", "message": {"content": [{"type": "text", "text": entry}]}}
                if isinstance(entry, str) else entry
            ) + "\n"
            for entry in entries
        ))
        return str(path)

    @staticmethod
    def launch(tool_use_id: str, result: str | list) -> list[dict]:
        return [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": tool_use_id, "name": "Bash", "input": {}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": tool_use_id, "content": result}]}},
        ]

    @staticmethod
    def user(content: str | list) -> dict:
        return {"type": "user", "message": {"content": content}}

    def test_background_work_still_running_holds_the_checks_until_it_reports(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        running = self.launch("toolu_1", "Command running in background with ID: b1x. Output is being written to: /t")
        self.assertEqual(self.run_hook("stop", transcript_path=self.transcript(*running)), {})
        done = self.user(
            "<task-notification>\n<task-id>b1x</task-id>\n<tool-use-id>toolu_1</tool-use-id>\n"
            "<status>completed</status>\n</task-notification>"
        )
        out = self.run_hook("stop", transcript_path=self.transcript(*running, done))
        self.assertEqual(out.get("decision"), "block")

    def test_an_async_agent_holds_the_checks_until_it_is_stopped(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        running = self.launch("toolu_2", [{"type": "text", "text": "Async agent launched successfully.\nagentId: a62f (internal)"}])
        self.assertEqual(self.run_hook("stop", transcript_path=self.transcript(*running)), {})
        stopped = self.user([{"type": "tool_result", "tool_use_id": "toolu_3",
                              "content": '{"message":"Successfully stopped task: a62f (review)"}'}])
        out = self.run_hook("stop", transcript_path=self.transcript(*running, stopped))
        self.assertEqual(out.get("decision"), "block")

    def test_a_background_task_silent_for_an_hour_no_longer_holds_the_checks(self) -> None:
        # A task can end without a notification ever reaching the transcript.
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        launched, result = self.launch("toolu_4", "Command running in background with ID: b4. Output: /t")
        result["timestamp"] = "2026-10-12T08:00:00.000Z"
        later = {**self.user("next prompt"), "timestamp": "2026-10-12T09:01:00.000Z"}
        out = self.run_hook("stop", transcript_path=self.transcript(launched, result, later))
        self.assertEqual(out.get("decision"), "block")

    def test_a_tool_result_that_quotes_a_launch_line_does_not_hold_the_checks(self) -> None:
        # Reading an old transcript or log prints these lines without starting anything.
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        quoted = self.launch("toolu_5", "grep hit: Command running in background with ID: b5. Output: /t")
        out = self.run_hook("stop", transcript_path=self.transcript(*quoted))
        self.assertEqual(out.get("decision"), "block")

    def test_an_unreadable_transcript_does_not_hold_the_checks(self) -> None:
        (self.repo / "a.py").write_text(lines(10) + lines(50, "new"))
        out = self.run_hook("stop", transcript_path=str(self.tmp / "nope.jsonl"))
        self.assertEqual(out.get("decision"), "block")

    def test_a_summary_without_the_diff_shape_does_not_block(self) -> None:
        # The shape reaches the user as the hook's own systemMessage.
        (self.repo / "a.py").write_text(lines(2) + lines(45, "other"))
        out = self.run_hook("stop", transcript_path=self.transcript("Done, the parser handles it now."))
        self.assertNotIn("decision", out)
        self.assertIn("+45 / -8", out["systemMessage"])

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

    def test_a_payload_that_is_not_an_object_never_fails_the_hook(self) -> None:
        for command in ("stop", "session-start"):
            proc = subprocess.run(
                [sys.executable, str(HOOK), command], input="[1]", cwd=self.repo,
                env={**GIT_ENV, "CLAUDE_CONFIG_DIR": str(self.config)}, capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unknown_subcommand_exits_2(self) -> None:
        proc = subprocess.run([sys.executable, str(HOOK), "bogus"], input="{}", capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
