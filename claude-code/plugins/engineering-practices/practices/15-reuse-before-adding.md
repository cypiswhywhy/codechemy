# Reuse before adding

- Before adding a helper, validator, formatter, client or constant, grep for the concept, not
  the name (`normali[sz]`, `slug`, `retry`, `to_path`). If nothing exists, say what you searched.
- Two call sites is the threshold for extracting. Generalise the existing code and use it in
  both, in the same change; never copy it or write a near-duplicate under another name.
- Put it where both callers already see it: base class, a module both import, or a free
  function, whichever seam the codebase uses. A new shared module is the last resort.
- The extraction is behaviour-preserving: its own `refactor:` commit, tests green either side,
  before the change that needed it.
- It is in scope even when it edits a file the task did not name. Widening an abstraction nothing
  in this change uses is not.
- Name in the summary the call sites that now share the code and the duplicate deleted with it.
