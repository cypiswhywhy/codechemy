# Small increments

- Prefer several small, independently reviewable and revertible changes over one large
  one. Order them: behaviour-preserving refactor first, then the feature, then follow-ups.
- Cleanup goes in its own commit(s) (`refactor: ...`), behaviour-preserving, tests green
  before and after, on the same branch as the change that motivated it.
- Each landing point is one independently shippable piece of value: reviewable on its own,
  revertible on its own, useful on its own once merged. That, and not a line count, is where
  a change is cut. Smaller is better where the seam is real; never split one piece of value
  across commits or PRs to keep them small, and never bundle two to save a round trip.
- When implementing a plan or task list, land each task (or one coherent group) as its own
  commit, and as its own PR where the workflow allows it. Many hundreds of changed lines are
  a prompt to look for a seam, not a limit: when it is one piece of value, land it whole and
  say so in the summary.
