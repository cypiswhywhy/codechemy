# Small increments

Name the landing points before writing, not after. A seam found in a finished diff is
almost always a file boundary rather than a boundary of value.

- Before the first line of code, say what the landing points are - the groups of a plan or
  task list where there is one, a one-line list of your own where there is not. Then implement
  them one at a time.
- The test for a landing point: merged on its own and stopped there, is someone better off,
  with the default branch still green and deployable? Code nothing calls yet, a half-wired
  feature and a flag nobody flips all fail it, and belong with the piece that completes them.
- A commit and a PR are not the same decision. A commit is free, so cut one at every coherent
  step: the behaviour-preserving refactor first, then the feature, then the follow-ups. A PR
  costs a review cycle, so cut one only where the test above passes.
- Keeping a change whole is the other half of this rule. Never split one piece of value to make
  the parts look smaller, and never bundle two to save a round trip. Size is not a seam: one
  piece of value lands whole whether it is 40 lines or 1000, and the summary says so.
- These are not seams: by file or directory; by layer (the schema, then the API, then the UI,
  none of them usable alone); "add the code" and then "wire it up"; tests apart from the code
  they cover, which "Test-driven by default" already rules out by committing at green.
- Cleanup goes in its own commit(s) (`refactor: ...`), behaviour-preserving, tests green before
  and after, on the same branch as the change that motivated it.
- Fewer complete increments beat more partial ones, and the number of PRs is no measure of
  progress. Hundreds of changed lines are a prompt to re-apply the test, not a limit.
