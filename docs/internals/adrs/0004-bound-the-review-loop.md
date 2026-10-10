# 0004. Bound the review loop

- **Status**: Accepted
- **Date**: 2026-09-21

## Context
Recorded retroactively from commit `a0c5b3e`. Over eleven PRs of one change, a same-model
reviewer raised 294 review threads; the loop took 31.6 h against 15.2 h of implementing; two PRs
ran to eight and nine cycles under a three-cycle cap; one session ran 32 h at a million tokens.

## Decision
- The local `/code-review` fallback runs one pass, at `medium`, on the code the PR changes,
  skipping planning prose.
- The three-cycle cap is counted from the fix commits on the branch, not from memory.
- `/apply-all-increments` stops after each merged increment, so the next starts in a fresh session.

## Consequences
- A compacted or resumed session cannot lose count of cycles.
- What one local pass misses is left to the user's own read of the PR.
- Long changes take more sessions, each with a small context.
