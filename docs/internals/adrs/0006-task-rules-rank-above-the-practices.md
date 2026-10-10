# 0006. The task's own rules rank above the practices

- **Status**: Accepted
- **Date**: 2026-10-02

## Context
Recorded retroactively from commit `bc7fcf0` and `engineering-practices-optimization.md`. The
SessionStart preamble said the practices OVERRIDE every default, which put them ahead of a task's
firm requirements, such as a documented rule that must win or output that must stay
byte-identical.

## Decision
The preamble ranks the task's requirements and the project's documented rules first. The
practices come next, and still override Claude Code's own defaults: they decide how to work,
not what to build.

## Consequences
- A task's explicit constraints win over, for example, "remove compatibility shims".
- The practices still beat Claude Code's defaults, such as a minimal diff.
