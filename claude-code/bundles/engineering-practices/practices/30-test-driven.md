# Test-driven by default

When a change alters behaviour and the project has an automated test harness, work
red-green-refactor. The test is the specification; the code is what makes it pass.

- Write the failing test first, from the requirement rather than from an implementation you
  already have in mind. Run it and watch it fail for the expected reason before writing
  production code; a test that passes on its first run has proven nothing.
- Write the smallest code that turns it green, then refactor with the tests still green.
  Commit at green, test and code together.
- One behaviour per test, named after the behaviour (`rejects an expired token`), not after
  the method it calls. Assert on outcomes, not on internals, so the refactor step stays free.
- A bug fix starts with a test that reproduces the bug: it fails on the current code, passes
  on the fix, and stays as the regression guard.
- A failing test is a bug report about the code, not about the test. Find the root cause
  first: read the assertion, trace the code path it exercises, and state why the code produces
  that output. Edit the test only once you have shown the business logic under it is correct
  and the test encodes a wrong or stale expectation, and say so in the summary. Never weaken
  assertions, add skips, or change expected values to match the current output to get green.
- Not applicable to docs, configuration, one-off scripts, and spikes the user has called
  spikes. Where the project has no harness, offer once to add one before the first behaviour
  change; if declined, or if the code has no reachable test seam, say so in the summary
  together with what would make it testable.
- Name in the summary the tests added or changed and the command that ran them, with its
  result.
