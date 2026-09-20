# Understand before you change

The most expensive defect available is a correct, well-tested implementation of the wrong
thing: no test, review or audit downstream catches it, because every one of them checks the
code against the intent rather than the intent against the need. Nothing else here recovers a
minute skipped at this point.

- Restate the request in one line as the outcome someone wants, not as the edit that was asked
  for. Where your restatement and the literal ask come apart, that gap is the thing to raise -
  before writing, not in the summary.
- Name the invariant: what is true of this system now and must still be true afterwards. A
  change with no invariant named has nothing to verify against but its own diff.
- Read one existing example of the same kind of thing before adding a new one. Matching the
  idiom the codebase already uses beats the idiom you would have chosen - and that read is
  usually where you find the helper that means you write far less ("Reuse before adding").
- Name the two or three ways the change can fail before writing it. That list is the test list
  ("Test-driven by default") and the failure modes worth handling ("Correct by construction").
- When two readings of the request lead to materially different work, ask. When they do not,
  state the assumption you picked and keep going. Blocking on a question you could have
  answered is its own failure.
- When the change alters a published contract, crosses a module boundary, or is hard to undo,
  run `/frame` first. Everything else wants the four lines above, not a document.
