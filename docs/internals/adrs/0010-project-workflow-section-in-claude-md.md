# 0010. Record per-project workflow choices in a CLAUDE.md section

- **Status**: Accepted
- **Date**: 2026-11-24

## Context
Some choices differ per project and cannot be read from the code: whether `/push` should go
to Copilot or straight to the local review, and whether the user wants to approve a plan before
code is written. `/frame` used to wait for approval whenever it framed (`2a45c99`), then waited only
when the user asked for the design (`4563d74`), since a session without `AskUserQuestion` has
nobody to answer. Neither fits every
project.

## Decision
`/kick-off` asks once and writes a `## Project workflow` section to the project's `CLAUDE.md`
or `CLAUDE.local.md`. Skills read its lines; a missing section or line means the plugin's
existing default (`Review: copilot`, `Plan approval: auto`). What the repo already shows, such as
an `openspec/` directory, is detected, not recorded.

## Consequences
- The choices live with the project's other instructions, as the opt-out marker does
  ([0007](0007-opt-out-marker-in-claude-md.md)), and can be shared or kept personal.
- No skill depends on `/kick-off` having run.
- `Plan approval: ask` works through the loaded instructions, not a hook, so a session can still
  miss it; plan mode would enforce it but would also stop the OpenSpec apply skills.
