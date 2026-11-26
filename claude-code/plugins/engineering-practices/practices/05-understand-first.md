# Understand before you change

A correct implementation of the wrong thing is the one defect nothing downstream catches.

- Restate the request in one line as the outcome wanted, not the edit asked for. Raise any gap
  between the two before writing.
- Name the invariant: what is true now and must still be true afterwards. That includes the
  rules of the domain the code models (money, time zones, units, a protocol), not only the
  code's own.
- Read one existing example of the same kind of thing before adding a new one, and match it.
- Name the two or three ways the change can fail before writing it. That is the test list.
- Ask only when two readings lead to materially different work and the user can answer;
  otherwise state the assumption and keep going. Without an `AskUserQuestion` tool nobody
  reads a question, and a turn ended on one ends the work.
- Run `/frame` first when the change alters a published contract, crosses a module boundary, or
  is hard to undo, then continue into the code in the same turn: framing is a step of the work,
  not a place to stop, unless the project's `## Project workflow` says `Plan approval: ask`.
  Everything else wants the four lines above, not a document.
- Record a decision of that size in an ADR (architecture decision record) in the same change:
  the context, the choice, the option rejected, and what it costs, because the next person to
  question it has only the code. Use the repo's ADR folder and template; with none, start
  `docs/internals/adrs/0001-<decision>.md`. A reversed decision gets a new ADR, not an edit.
