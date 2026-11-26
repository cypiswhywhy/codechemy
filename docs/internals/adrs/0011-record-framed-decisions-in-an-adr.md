# 0011. Record every framed decision in an ADR

- **Status**: Accepted
- **Date**: 2026-11-26

## Context
Only `/frame` Step 5 and `/maintain` wrote ADRs, and only where the repo already kept them and
the decision "will be asked about again". In an ordinary session nothing asked for one, so the
decisions that cost the most to reverse (a published contract, a module boundary, anything hard
to undo) left no record of why.

## Decision
Practice 05 tells the agent to record any decision at the `/frame` bar in an ADR, in the same
change. It uses the repo's ADR folder and template; a repo with none gets
`docs/internals/adrs/`, the location the `docs-*` skills already use, and the template in
`skills/frame/references/adr-template.md`: Problem, Options with the pros and cons of each,
Decision and why, and Success criteria where something can be measured. `/frame` Step 5 writes
the ADR instead of deciding whether to.

## Consequences
- The rule is always on, so it applies even when `/frame` is not run.
- A repo with no ADRs gets a new folder on its first framed change. This reverses Step 5's old
  "do not introduce a new location".
- Rejected: keeping the commit message body as the record when the repo has no ADRs. It is not
  found by anyone browsing the docs, and the practice would then depend on the repo's history.
