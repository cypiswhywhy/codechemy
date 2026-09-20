# Reuse before adding

Before writing something new, find out whether the repository already does it. The cheapest
line of code is the one already written and tested.

- Search before you write. Before adding a helper, validator, formatter, client or constant,
  grep for the concept rather than the name (`normali[sz]`, `slug`, `retry`, `to_path`) and
  read what comes back. When you conclude nothing exists, say in the summary what you searched
  for.
- Two call sites is the threshold for extracting, not three. The moment a second place needs
  behaviour a first place already has, generalise the existing one and use it in both, in the
  same change. Do not copy it, and do not write a near-duplicate under a different name.
- Put it where both callers can already see it: pull the method up to the shared base class,
  move it into a module both import, or drop it to a free function - whichever seam the
  codebase already uses. A new shared module is the last resort, not the first.
- Extracting is behaviour-preserving, so it lands as its own `refactor:` commit with the
  existing tests green either side, before the change that needed it.
- This is in scope, always. Generalising a helper this change needs is part of the change even
  when it edits a class or file the task did not name, and the scope boundary in "Leave the
  code smaller than you found it" does not apply to it. Widening an abstraction that nothing in
  this change uses is still a separate task.
- Name in the summary which call sites now share the extracted code, and the duplicate you
  deleted with it. An extraction that leaves the original copy in place has added, not reused.
