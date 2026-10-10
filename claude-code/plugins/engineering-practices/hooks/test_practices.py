#!/usr/bin/env python3
"""Tests for practices.py. Run: python3 test_practices.py

The hook is driven the way Claude Code drives it: a JSON payload on stdin, stdout becomes
the session's added context.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE / "practices.py"
PRACTICES = sorted((HERE.parent / "practices").glob("*.md"))


def run(cwd: Path = HERE) -> str:
    proc = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps({"cwd": str(cwd)}),
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


class PracticesCase(unittest.TestCase):
    def test_emits_every_practice_in_full(self) -> None:
        output = run()
        for practice in PRACTICES:
            self.assertIn(practice.read_text().strip(), output)

    def test_orders_practices_by_filename(self) -> None:
        output = run()
        positions = [output.index(p.read_text().strip().splitlines()[0]) for p in PRACTICES]
        self.assertEqual(positions, sorted(positions))

    def test_marks_the_practices_as_overriding_defaults(self) -> None:
        self.assertIn("override claude code's default behaviour", run().lower())

    def test_ranks_the_task_and_project_rules_above_the_practices(self) -> None:
        preamble = run().split("\n\n", 1)[0].lower()
        self.assertIn("the task's own requirements and the project's documented rules come first",
                      preamble)

    def test_a_project_opting_out_gets_no_practices(self) -> None:
        for claude_md in ("CLAUDE.md", ".claude/CLAUDE.md"):
            with self.subTest(claude_md), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / claude_md).parent.mkdir(exist_ok=True)
                (Path(tmp) / claude_md).write_text("# Notes\n\n<!-- engineering-practices: off -->\n")
                self.assertEqual(run(Path(tmp)), "")

    def test_the_marker_at_the_repository_root_covers_its_subdirectories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            (Path(tmp) / "CLAUDE.md").write_text("<!-- engineering-practices: off -->\n")
            (Path(tmp) / "sub").mkdir()
            self.assertEqual(run(Path(tmp) / "sub"), "")


if __name__ == "__main__":
    unittest.main(verbosity=0 if "-q" in sys.argv else 1, argv=[a for a in sys.argv if a != "-q"])
