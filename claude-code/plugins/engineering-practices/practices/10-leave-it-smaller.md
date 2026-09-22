# Leave the code smaller than you found it

Every change is also a maintenance pass over the code it touches; this wins over "minimal diff".

- In what you touch, remove dead code, duplicated helpers, unused imports, parameters and flags,
  stale comments and compatibility shims. A net-negative diff is the preferred outcome.
- Replace, don't accumulate: when a new path supersedes an old one, delete the old one in the
  same change. Keep both only when the user asks or a published interface depends on it, and
  say which in the summary.
- Delete, don't deprecate: no commented-out code, `TODO: remove`, or `_old`/`_v2` suffixes.
- No defensive code for a case that cannot happen: no try/except around code that does not
  raise, no null check on what the type guarantees, no fallback for an unreachable branch, no
  flag or knob with one caller. Validating data from outside is not this ("Correct by
  construction").
- Prove, then delete: run the project's `## Maintenance toolbox` commands and grep for callers,
  tests, configs and docs. Without a toolbox section, offer `/maintenance-toolbox` once; until
  then the caller grep is the proof.
- Tidy what the change touches and its neighbourhood. A wider refactor is a separate task; name
  it in the summary. Extracting a helper this change needs is not wider ("Reuse before adding").
- End every summary with the diff shape (`+N / -M`, files). Zero removals in a change to
  existing code is a smell; say why.
