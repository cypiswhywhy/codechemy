#!/usr/bin/env python3
"""
session-end-reviewer.py — STUB for future "missing call" detection.

WHY THIS IS A STUB
------------------
Hooks can only observe events that happen. There is no event for a call that
*should* have been made but wasn't, so the PreToolUse/PostToolUse hooks in this
plugin cannot flag "missing" invocations. That analysis has to run at the end of
a session by comparing what the session was *trying* to do against what was
actually called.

INTENDED DESIGN (not yet implemented)
-------------------------------------
Wire this as a SessionEnd hook. On stdin it would receive session_id,
transcript_path, and cwd. It would then:
  1. Read the transcript at `transcript_path` (the session's messages/tool use).
  2. Read this session's rows from the audit JSONL (filter by session_id).
  3. Diff intent vs. actuals — e.g. the user/task implied an Atlassian update
     but no mcp__atlassian__* call was logged -> candidate "missing call".
     (This step is heuristic and likely wants a model call to judge intent.)
  4. Append findings to a review log and/or a separate Confluence section.

To enable later, add to hooks/hooks.json:

    "SessionEnd": [
      { "hooks": [ { "type": "command",
        "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/session-end-reviewer.py\"" } ] }
    ]

For now this reads stdin and exits 0 without doing anything.
"""
import sys

def main():
    try:
        sys.stdin.read()
    except Exception:
        pass
    # TODO: implement intent-vs-actual diff described above.
    return 0

if __name__ == "__main__":
    sys.exit(main())
