# Small increments

- Name the landing points before the first line of code: the groups of a plan or task list, or a
  one-line list of your own. Implement them one at a time.
- A landing point passes one test: merged on its own and stopped there, is someone better off,
  with the default branch still green? Uncalled code, a half-wired feature and an unflipped flag
  fail it and belong with the piece that completes them.
- Commits are free: cut one at every coherent step, refactor first, then the feature, then the
  follow-ups. A PR costs a review cycle: cut one only where the test above passes.
- Never split one piece of value to look smaller, and never bundle two to save a round trip.
  Size is not a seam: one piece of value lands whole at 40 lines or 1000, and the summary says so.
- Not seams: by file or directory; by layer; "add the code" then "wire it up"; tests apart from
  the code they cover.
- Cleanup goes in its own `refactor:` commit, tests green before and after, on the same branch.
- Fewer complete increments beat more partial ones; the PR count measures nothing.
