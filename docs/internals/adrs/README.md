# Architecture decision records

An ADR records one decision that shaped how the plugin works: the context that forced it, what
was decided, and what it costs. Write one when a change alters how the plugin works, not just
what it says.

To add one: copy the template to `NNNN-<decision-in-kebab-case>.md` with the next number, and add
a row below. Accepted ADRs are not edited; a reversed decision gets a new ADR, and the old one's
Status becomes `Superseded by [NNNN](NNNN-<slug>.md)`.

```markdown
# NNNN. Title stated as the decision

- **Status**: Proposed | Accepted | Superseded by [NNNN](NNNN-other.md)
- **Date**: YYYY-MM-DD

## Context
What forced a decision. Constraints, and what was true at the time.

## Decision
What was chosen, in the active voice.

## Consequences
What this makes easy, what it makes hard, and what it rules out.
```

| # | Decision | Status | Date |
|---|---|---|---|
| [0001](0001-ship-as-a-plugin-with-the-contract-in-a-hook.md) | Ship as a plugin, with the contract printed by a SessionStart hook | Accepted | 2026-09-09 |
| [0002](0002-cut-increments-at-shippable-value.md) | Cut increments at a shippable piece of value, not at a line count | Accepted | 2026-09-14 |
| [0003](0003-fall-back-to-local-review-without-copilot.md) | Fall back to a local /code-review when Copilot is unavailable | Accepted | 2026-09-18 |
| [0004](0004-bound-the-review-loop.md) | Bound the review loop | Accepted | 2026-09-21 |
| [0005](0005-practices-as-rules-without-reasoning.md) | State the practices as rules, without the reasoning | Accepted | 2026-09-22 |
| [0006](0006-task-rules-rank-above-the-practices.md) | The task's own rules rank above the practices | Accepted | 2026-10-02 |
| [0007](0007-opt-out-marker-in-claude-md.md) | Let a project opt out with a CLAUDE.md marker | Accepted | 2026-10-10 |
