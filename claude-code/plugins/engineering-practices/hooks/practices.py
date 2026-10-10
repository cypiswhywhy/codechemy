#!/usr/bin/env python3
"""SessionStart hook: put the engineering practices into every session's context.

Reads `practices/*.md` in name order and writes them to stdout, which Claude Code adds to
the session. This is the contract layer of the plugin: the rules the agent should hold for
the whole session, stated as rules so they cost the context they are worth. A project whose
CLAUDE.md carries OPT_OUT gets nothing from either hook.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PRACTICES = Path(__file__).resolve().parent.parent / "practices"
OPT_OUT = "<!-- engineering-practices: off -->"

PREAMBLE = (
    "Engineering practices, from the engineering-practices plugin, for this and every session. "
    "The task's own requirements and the project's documented rules come first. Below them, "
    "these practices override Claude Code's default behaviour where the two conflict: they "
    "decide how to work, not what to build."
)


def project_instructions(cwd: str) -> str:
    """The project's CLAUDE.md files, read from the repository root, or from cwd outside one."""
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True,
            timeout=10, check=False,
        ).stdout.strip() or cwd
    except (OSError, subprocess.SubprocessError):
        root = cwd
    text = ""
    for candidate in (Path(root) / "CLAUDE.md", Path(root) / ".claude" / "CLAUDE.md"):
        try:
            text += candidate.read_text(errors="replace")
        except OSError:
            pass
    return text


def payload_cwd() -> str:
    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except ValueError:
        payload = {}
    return payload.get("cwd") or os.getcwd()


def main() -> int:
    if OPT_OUT in project_instructions(payload_cwd()):
        return 0
    bodies = [p.read_text().strip() for p in sorted(PRACTICES.glob("*.md"))]
    if not bodies:
        sys.exit(f"error: no practices/*.md in {PRACTICES}")
    print("\n\n".join([PREAMBLE, *bodies]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
