# Code review lessons

Tallies recurring classes of mistake caught in code review. One `##` section per class; one bullet per occurrence: date, PR URL, short phrase naming the instance. Three occurrences from independent PRs is the threshold for proposing a preventive rule.

## New code added outside a hook's never-fail guard, trusting its input's shape

- 2026-10-10, https://github.com/cypiswhywhy/codechemy/pull/16, opt-out check before the try; payload assumed to be a JSON object
