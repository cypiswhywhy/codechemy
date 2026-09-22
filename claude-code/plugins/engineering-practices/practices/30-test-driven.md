# Test-driven by default

When a change alters behaviour and the project has a test harness, work red-green-refactor.

- Write the failing test first, from the requirement, and watch it fail for the expected reason.
  A test that passes on its first run has proven nothing.
- Write the smallest code that turns it green, refactor on green, commit test and code together.
- One behaviour per test, named after the behaviour (`rejects an expired token`); assert on
  outcomes, not internals.
- A bug fix starts with a test that reproduces the bug and stays as the regression guard.
- A failing test is a bug report about the code. Root-cause the code first; edit the test only
  once the logic under it is shown correct and the expectation shown stale, and say so in the
  summary. Never weaken an assertion, add a skip, or change an expected value to get green.
- Not applicable to docs, configuration, one-off scripts and declared spikes. Without a harness,
  offer once to add one; if declined or there is no test seam, say so and what would make it
  testable.
- Name in the summary the tests added or changed and the command that ran them, with its result.
