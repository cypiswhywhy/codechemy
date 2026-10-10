# Practices

The contract the `SessionStart` hook prints into every session. Each is one file in
`claude-code/plugins/engineering-practices/practices/`, printed in name order; the files are the
full text, this page is the index.

- [**05-understand-first.md**](../../claude-code/plugins/engineering-practices/practices/05-understand-first.md): the most expensive defect is a correct implementation of the
  wrong thing, and nothing downstream catches it. Restate the request as an outcome, name the
  invariant (the domain's rules included), read one existing example of the same kind of
  thing, name the two or three ways it can fail, ask only where two readings lead to different
  work - and run
  [`/frame`](../../claude-code/plugins/engineering-practices/skills/frame/SKILL.md) when the change touches a contract, crosses a module
  boundary or is hard to undo.
- [**10-leave-it-smaller.md**](../../claude-code/plugins/engineering-practices/practices/10-leave-it-smaller.md): every change is also a maintenance pass over the code it
  touches. Tidy as you go, replace don't accumulate, delete don't deprecate, no defensive code
  the task does not need, prove then delete, a scope boundary, and the diff shape in every summary.
- [**15-reuse-before-adding.md**](../../claude-code/plugins/engineering-practices/practices/15-reuse-before-adding.md): grep for the concept before writing a helper; the second call
  site is the threshold for extracting, not the third; generalise the existing code and put it
  where both callers already see it (base class, shared module, free function) rather than
  copying it; the extraction lands as its own `refactor:` commit, and is in scope even when it
  edits a file the task did not name.
- [**20-small-increments.md**](../../claude-code/plugins/engineering-practices/practices/20-small-increments.md): name the landing points before writing, because a seam found in a
  finished diff is a file boundary; one test for each of them (merged on its own and stopped
  there, is someone better off with the default branch still green); commits are free and cut at
  every coherent step, a PR costs a review cycle and is cut only at a real seam; one piece of
  value lands whole at any size; the splits that only look like seams are named so they can be
  refused.
  The [`/apply-increment`](../../claude-code/plugins/engineering-practices/skills/apply-increment/SKILL.md) and
  [`/apply-all-increments`](../../claude-code/plugins/engineering-practices/skills/apply-all-increments/SKILL.md) skills carry this out for an
  OpenSpec project.
- [**30-test-driven.md**](../../claude-code/plugins/engineering-practices/practices/30-test-driven.md): red-green-refactor whenever a change alters behaviour and the project
  has a test harness. Failing test first and seen failing, simplest code to green, refactor on
  green; bug fixes start with a reproducing test; a red test means root-cause the code, and the test
  changes only once the logic under it is shown correct; not
  applicable to docs, config, one-off scripts and declared spikes, and the summary says so.
- [**35-correct-by-construction.md**](../../claude-code/plugins/engineering-practices/practices/35-correct-by-construction.md): the defects the review loop and the audit find one cycle
  at a time, written correctly the first time instead. Validate where data crosses into your
  code and trust it inside; propagate errors with context and never swallow one; name shared
  state before creating it; make anything reachable twice safe twice; release on the error path;
  keep untrusted input out of interpreters and credentials out of logs.
- [**40-say-less.md**](../../claude-code/plugins/engineering-practices/practices/40-say-less.md): comments carry the *why* only; one-line docstrings stating the contract,
  none at all where the name and signature already say it; length only for a reason outside the
  code; no change narration, `TODO`s or commented-out code; match the density of the file.
- [**45-write-plainly.md**](../../claude-code/plugins/engineering-practices/practices/45-write-plainly.md): what goes to the reader - chat, questions, summaries, PR descriptions,
  commit bodies - ends with the answer or the question, in short sentences and common words,
  with the concrete `file:line`, command or number; one topic per message; no preamble, recap,
  closing offer or empty hedge; the summary items the other practices require stay, one line
  each.
