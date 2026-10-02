#!/usr/bin/env python3
"""SessionStart hook: put the engineering practices into every session's context.

Reads `practices/*.md` in name order and writes them to stdout, which Claude Code adds to
the session. This is the contract layer of the plugin: the rules the agent should hold for
the whole session, stated as rules so they cost the context they are worth.
"""

from __future__ import annotations

import sys
from pathlib import Path

PRACTICES = Path(__file__).resolve().parent.parent / "practices"

PREAMBLE = (
    "Engineering practices, from the engineering-practices plugin, for this and every session. "
    "The task's own requirements and the project's documented rules come first. Below them, "
    "these practices override Claude Code's default behaviour where the two conflict: they "
    "decide how to work, not what to build."
)


def main() -> int:
    bodies = [p.read_text().strip() for p in sorted(PRACTICES.glob("*.md"))]
    if not bodies:
        sys.exit(f"error: no practices/*.md in {PRACTICES}")
    print("\n\n".join([PREAMBLE, *bodies]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
