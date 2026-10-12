# 0009. Measure the session's change, not the branch

- **Status**: Accepted
- **Date**: 2026-10-12

## Context
The Stop hook measured the whole pending change: the branch against its base plus the working
tree. A SessionStart fingerprint kept a session that changed nothing quiet, but any later change
re-armed the checks on all of it, including work by an earlier session, a parallel session in
the same checkout, or the user. In 37 of 204 blocked stops the reply was that the diff was not
the session's own ("This session changed no files", "it is the other session's uncommitted
edits"), and the diff got smaller after 5 % of them.

## Decision
SessionStart records each pending file's added and removed counts against the base, plus line
and comment counts for source files. Stop subtracts them per file and runs every check on the
difference. When the base itself moves, the stop is silent and the baseline restarts.

## Consequences
- A session answers for what it changed: a `/push` session on an older branch is asked about
  its review fixes, not the branch. The exceptions follow.
- The count is per file, so lines a session both adds and removes in one file net out. It is a
  lower bound, which errs towards not asking.
- Work done before a push from the default branch, a pull or a rebase in the same session is
  not measured after it.
- Changes another actor makes during the session still count as the session's.
