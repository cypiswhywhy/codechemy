#!/usr/bin/env python3
"""Tests for practices.py. Run: python3 test_practices.py

The hook is driven the way Claude Code drives it: a JSON payload on stdin, stdout becomes
the session's added context.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE / "practices.py"
PRACTICES = sorted((HERE.parent / "practices").glob("*.md"))


def run() -> str:
    proc = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps({"cwd": str(HERE)}),
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

    def test_marks_the_practices_as_binding(self) -> None:
        self.assertIn("override", run().lower())


if __name__ == "__main__":
    unittest.main(verbosity=0 if "-q" in sys.argv else 1, argv=[a for a in sys.argv if a != "-q"])
