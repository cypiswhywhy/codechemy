# 0007. Let a project opt out with a CLAUDE.md marker

- **Status**: Accepted
- **Date**: 2026-10-10

## Context
Recorded retroactively from PR #16. The plugin is installed for the user, so it runs in every
project, including ones that are not code: notes, a task system, research. There the
practices and the Stop hook's questions about tests and change size do not apply. Disabling the
plugin in project settings works, but lives outside the project's own instructions and also
removes the skills.

## Decision
`<!-- engineering-practices: off -->` in a project's `CLAUDE.md` or `.claude/CLAUDE.md`, read
from the git root or the session's directory, silences both hooks. It follows the existing
`<!-- maintenance-toolbox: none -->` opt-out.

## Consequences
- The opt-out is written down in the project, next to its other instructions.
- Skills stay available there.
- The marker matches as plain text anywhere in those files, so quoting it verbatim also opts out.
