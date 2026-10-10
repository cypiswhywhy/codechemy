# 0003. Fall back to a local /code-review when Copilot is unavailable

- **Status**: Accepted
- **Date**: 2026-09-18

## Context
Recorded retroactively from commit `dfa4d3a`. Copilot code review can be disabled for a
repository, or the account can be out of premium requests. `/push` had no answer: an unreachable
reviewer ended the run, and a request that registered but never produced a review waited forever.

## Decision
`/push` routes to the local `/code-review` skill on any of three signals: a well-formed reviewer
request that still fails, a Copilot notice in place of a review, or a wait of about 20 minutes.
Once it falls back, the local reviewer owns the gate for the rest of the run.

## Consequences
- A PR is never left unreviewed just because Copilot is missing.
- The fallback reviewer is the same model that wrote the change, so it is not independent;
  `/push` says so in its hand-off.
- The rest of the loop no longer assumes the Copilot bot.
