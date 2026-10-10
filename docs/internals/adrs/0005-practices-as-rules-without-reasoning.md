# 0005. State the practices as rules, without the reasoning

- **Status**: Accepted
- **Date**: 2026-09-22

## Context
Recorded retroactively from commit `3c2dcfa`. The practices are printed into every session,
and again on every compaction and resume. The text was 12,230 bytes, much of it paragraphs
arguing for the rules.

## Decision
Keep every rule (46 before, 46 after) and drop the argument. Each rule carries its reason in at
most one clause.

## Consequences
- The SessionStart text fell to 7,737 bytes.
- The longer reasoning lives in commit history and these docs, not in the session.
