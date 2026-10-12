# 0002. Cut increments at a shippable piece of value, not at a line count

- **Status**: Accepted; the Stop-hook question superseded by [0008](0008-block-only-on-checks-that-change-the-code.md)
- **Date**: 2026-09-14

## Context
Recorded retroactively from commits `8b8b69f`, `4f1510e` and `b804a8b`. The small-increments
practice named 400 changed lines as the point to stop, and `/apply-increment` turned that into
changes split across seven PRs, none useful on its own.

## Decision
A landing point is one independently shippable piece of value. Size is a preference, not the
rule. At 400 lines the Stop hook asks which seams were named up front instead of asking for a
split.

## Consequences
- One piece of value lands whole, at any size.
- Splits by file, by layer, or "add the code, then wire it up" are refused as seams.
- Large PRs remain possible and must say why they are one piece.
