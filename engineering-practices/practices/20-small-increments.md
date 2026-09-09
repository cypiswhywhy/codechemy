# Small increments

- Prefer several small, independently reviewable and revertible changes over one large
  one. Order them: behaviour-preserving refactor first, then the feature, then follow-ups.
- Cleanup goes in its own commit(s) (`refactor: ...`), behaviour-preserving, tests green
  before and after, on the same branch as the change that motivated it.
- Around 400 changed lines is the point to stop and land what is complete before adding
  more. When implementing a plan or task list, land each task (or one coherent group) as
  its own commit, and as its own PR where the workflow allows it.
- For an OpenSpec change, use `/apply-increment` rather than applying the whole task list
  in one run: it implements one task group, lands it as its own PR, and stops.
  `/apply-all-increments` repeats that to the end of the change, pausing only for each merge.
