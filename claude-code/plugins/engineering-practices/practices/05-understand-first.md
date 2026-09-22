# Understand before you change

A correct implementation of the wrong thing is the one defect nothing downstream catches.

- Restate the request in one line as the outcome wanted, not the edit asked for. Raise any gap
  between the two before writing.
- Name the invariant: what is true now and must still be true afterwards.
- Read one existing example of the same kind of thing before adding a new one, and match it.
- Name the two or three ways the change can fail before writing it. That is the test list.
- Ask only when two readings lead to materially different work; otherwise state the assumption
  and keep going.
- Run `/frame` first when the change alters a published contract, crosses a module boundary, or
  is hard to undo. Everything else wants the four lines above, not a document.
