# 0008. Block the stop only on checks that lead to a change

- **Status**: Accepted
- **Date**: 2026-10-12

## Context
Across 204 blocked stops in 129 sessions (2026-09-09 to 2026-10-12), the add-only questions
were followed by a smaller diff in 20 % of cases, each a real cleanup: merged duplicate
fixtures, deleted dead methods, shared copied CSS. The 400-line question ([0002](0002-cut-increments-at-shippable-value.md))
and the missing-diff-shape check fired 112 and 91 times; the diff got smaller after 6 % and 8 %
of them, and only because another check blocked in the same stop. Their replies were
explanations ("already split", "one piece of value") or one appended line, at about 74k output
tokens in all and a turn of the user's reading each time.

## Decision
The Stop hook no longer blocks for a change's size or for a summary without `+N / -M`. The
shape it already shows the user as a `systemMessage` carries the `large change` flag instead.
Blocking stays for the add-only, test and prose checks.

## Consequences
- 90 of the 204 blocks would not have happened, with no cleanup lost.
- Naming landing points up front rests on the practice and on `/frame` and `/apply-increment`,
  not on a late question.
- A summary can omit the diff shape; the user still sees it in the hook's message.
