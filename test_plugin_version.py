"""A change to the plugin must raise its version, or installs keep the old copy. Run: pytest"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = "claude-code/plugins/engineering-practices/"
MANIFEST = PLUGIN + ".claude-plugin/plugin.json"


def version_problem(changed: list[str], base: str, head: str) -> str | None:
    """Why the version must go up, or None when it need not."""
    if not any(path.startswith(PLUGIN) for path in changed):
        return None
    if tuple(map(int, head.split("."))) > tuple(map(int, base.split("."))):
        return None
    return f"the plugin changed but {MANIFEST} is still at {head} (main has {base}): raise `version`"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()


class VersionProblemCase(unittest.TestCase):
    def test_a_plugin_change_with_a_raised_version_passes(self) -> None:
        self.assertIsNone(version_problem([PLUGIN + "practices/05-understand-first.md"], "3.2.0", "3.3.0"))

    def test_a_plugin_change_with_the_same_version_fails(self) -> None:
        problem = version_problem([PLUGIN + "skills/frame/SKILL.md"], "3.2.0", "3.2.0")
        self.assertIn(MANIFEST, problem)

    def test_a_lowered_version_fails(self) -> None:
        self.assertIsNotNone(version_problem([PLUGIN + "hooks/practices.py"], "3.2.0", "3.1.9"))

    def test_versions_compare_as_numbers_not_text(self) -> None:
        self.assertIsNone(version_problem([PLUGIN + "hooks/practices.py"], "3.9.0", "3.10.0"))

    def test_a_change_outside_the_plugin_needs_no_bump(self) -> None:
        self.assertIsNone(version_problem(["docs/reference/practices.md", "CLAUDE.md"], "3.2.0", "3.2.0"))


class ThisBranchCase(unittest.TestCase):
    def test_this_branch_raises_the_version_if_it_changes_the_plugin(self) -> None:
        if subprocess.run(["git", "rev-parse", "--verify", "-q", "origin/main"], cwd=HERE, capture_output=True).returncode:
            self.skipTest("no origin/main to compare with")
        base = git("merge-base", "HEAD", "origin/main")
        changed = git("diff", "--name-only", "--no-renames", base).splitlines()
        changed += git("ls-files", "--others", "--exclude-standard").splitlines()
        base_version = json.loads(git("show", f"origin/main:{MANIFEST}"))["version"]
        head_version = json.loads((HERE / MANIFEST).read_text())["version"]
        problem = version_problem(changed, base_version, head_version)
        self.assertIsNone(problem, problem)


if __name__ == "__main__":
    unittest.main()
