"""Tests for `make check`. Run: pytest test_make_check.py"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = sorted(p.parent.name for p in (HERE / "claude-code/plugins/engineering-practices/skills").glob("*/SKILL.md"))


def check_lines() -> list[str]:
    proc = subprocess.run(["make", "--no-print-directory", "check"], cwd=HERE, capture_output=True, text=True, check=False)
    return proc.stdout.splitlines()


class MakeCheckCase(unittest.TestCase):
    def test_lists_every_skill_once(self) -> None:
        names = [line.split()[1] for line in check_lines() if line.startswith(("ok ", "MISSING "))]
        for skill in SKILLS:
            self.assertEqual(names.count(skill), 1, skill)

    def test_skill_without_prerequisites_is_ok(self) -> None:
        self.assertIn("ok        kick-off", check_lines())

    def test_every_prerequisite_names_a_skill_or_the_plugin(self) -> None:
        block = re.search(r"^PREREQS := \\\n((?:\t.*\n)+)", (HERE / "Makefile").read_text(), re.M)
        names = [line.strip().split(":")[0] for line in block.group(1).splitlines()]
        self.assertTrue(names)
        for name in names:
            self.assertIn(name, [*SKILLS, "engineering-practices"])


if __name__ == "__main__":
    unittest.main()
