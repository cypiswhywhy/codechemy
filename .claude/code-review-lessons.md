# Code review lessons

Tallies recurring classes of mistake caught in code review. One `##` section per class; one bullet per occurrence: date, PR URL, short phrase naming the instance. Three occurrences from independent PRs is the threshold for proposing a preventive rule.

## New code added outside a hook's never-fail guard, trusting its input's shape

- 2026-10-10, https://github.com/cypiswhywhy/codechemy/pull/16, opt-out check before the try; payload assumed to be a JSON object

## Renaming a user-facing name without a breaking-change version bump

- 2026-11-20, https://github.com/cypiswhywhy/codechemy/pull/19 - renamed two slash-command skills, bumped minor

## A new "wait for the user" rule that forgets sessions nobody watches
- 2026-11-24, https://github.com/cypiswhywhy/codechemy/pull/20 - `Plan approval: ask` would stop `claude -p` and subagents

## A recorded choice overwritten by a run that never asked the user
- 2026-11-24, https://github.com/cypiswhywhy/codechemy/pull/20 - re-running /kick-off reset skipped answers to defaults
- 2026-11-24, https://github.com/cypiswhywhy/codechemy/pull/21 - headless /apply-increment wrote `Jira: none`; /kick-off without Atlassian wrote `Jira: off`

## A path resolved from the current folder instead of the file that names it
- 2026-11-24, https://github.com/cypiswhywhy/codechemy/pull/23 - `make -f` from another folder found no skills and passed

## Changing a rule in one place while another passage still states the old one
- 2026-11-26, https://github.com/cypiswhywhy/codechemy/pull/24 - /frame Step 5 now writes an ADR; its intro and Rules still said "no file"

## Checking against where the branch started instead of where main is now
- 2026-11-26, https://github.com/cypiswhywhy/codechemy/pull/26 - version guard read the merge-base's version, so two branches could ship the same bump
