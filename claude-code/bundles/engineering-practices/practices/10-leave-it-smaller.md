# Leave the code smaller than you found it

Every change is also a maintenance pass over the code it touches. Where this conflicts
with a "minimal diff, stay in scope" default, this section wins.

- When you touch a function, file or module you own its tidiness: remove the dead code,
  duplicated helpers, unused imports/parameters/flags, stale comments and compatibility
  shims you find there. A net-negative diff is the preferred outcome.
- Replace, don't accumulate. When a new code path supersedes an old one, delete the old one
  in the same change. Keep both only when the user asks for it or a published interface
  depends on it, and name which in the summary.
- Delete, don't deprecate. No commented-out code, no `TODO: remove`, no `_old`/`_v2`
  suffixes left behind.
- Add no defensive code the task does not require: no try/except wrappers, null checks,
  fallbacks, feature flags or config knobs for cases that cannot happen, and no comments
  that restate the code.
- Prove, then delete. Before removing anything, run the commands in the project's
  `## Maintenance toolbox` section (in its CLAUDE.md) and grep for callers, tests, configs
  and docs that name it. If the project has no toolbox section, offer once to run
  `/maintenance-toolbox`; until it exists, the caller grep is the proof.
- Scope boundary: tidy what the change touches and its immediate neighbourhood. A wider
  refactor is a separate task; name it in the summary instead of doing it.
- End every summary with the diff shape (`+N / -M`, files touched). Zero removals in a
  change to existing code is a smell; say why when that is the case.
