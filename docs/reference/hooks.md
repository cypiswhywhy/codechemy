# Hooks

Two hooks, registered in `claude-code/plugins/engineering-practices/hooks/hooks.json`. Both stay
silent in a project that opts out ([../usage/opt-out.md](../usage/opt-out.md)).

| Event | Script | Does |
|---|---|---|
| `SessionStart` | `hooks/practices.py` | prints the [practices](practices.md) into the session |
| `SessionStart` | `hooks/leave_it_smaller.py session-start` | records what is already pending, so the session answers only for its own changes; hints at `/maintenance-toolbox` |
| `Stop` | `hooks/leave_it_smaller.py stop` | measures the change and may block the stop once |

## `practices` (`hooks/practices.py`)

Concatenates `practices/*.md` in name order behind a preamble that ranks them: the task's own
requirements and the project's documented rules first, then these practices, which override
Claude Code's conflicting defaults. Claude Code adds the output to the session's context.
Editing a practice takes effect in the next session.

## `leave-it-smaller` (`hooks/leave_it_smaller.py`)

One script, two events. `stop` measures what this session changed: the pending change (branch vs
merge-base with `main`/`master` plus working tree; on the default branch, unpushed commits plus
working tree; untracked files count as new, binaries are ignored), less what was already pending
when the session started. Edits someone else makes in the same checkout during the session count
as the session's. It acts per stop:

| Condition (defaults) | Action |
|---|---|
| no repository, or no change by this session | silent |
| a background command or agent the session started has not reported back (for up to an hour) | silent: the stop is a pause, not the hand-back, so the checks wait for the next stop |
| the session gained ≥ 40 lines and lost < 10 % of that | **block once per session** with the diff shape and three questions: does it duplicate what already exists, did it supersede a path still in the tree, is there anything dead in what it touched |
| source files changed, no test changed, and the repo has tests | **block once per session** asking which behaviour changed and what now covers it - or to say that none did, with the test command and its result |
| a source file grew ≥ 20 lines, ≥ 40 % of them comments or docstrings, and 15 points past the file's own density | **block once per session** naming the files and asking for the pass "Say less in the code" describes: delete comments that narrate or restate, cut docstrings to the contract |
| otherwise, when the shape changed since the last stop | one-line `systemMessage` with `+N / -M across F files`, flagged `add-only` or `large change` (total ≥ 400 lines) when it is |

The change's size and whether the summary states `+N / -M` are shown, not asked: questions about
them led to explanations rather than changes ([ADR 0008](../internals/adrs/0008-block-only-on-checks-that-change-the-code.md)).
Bounded by construction: never while the agent is already continuing because of a stop
hook, never twice for the same diff, each check at most once per session, at most two blocks per
session in all; after that the smell is still shown to you but the agent is not interrupted.

`session-start` records each pending file's added and removed lines (and, for source files, its
line and comment counts). The session's own change is then measured per file as the change in
those counts, so lines it adds and removes within one file net out, and undoing earlier work
counts as removal. When the base moves (a push or pull on the default branch, a branch switch),
the counts no longer line up: that stop is silent and the baseline starts again from there. A
session with no recorded start, such as one already running when the plugin was installed, is
measured on the whole pending change. `session-start` also tells the agent to offer
`/maintenance-toolbox` once when the repository's `CLAUDE.md` has no `## Maintenance toolbox`.

### Settings

Environment variables, set in a shell or in a settings file's `env` block.

| Variable | Default | Meaning |
|---|---|---|
| `LEAVE_IT_SMALLER_MIN_ADDED` | `40` | added lines before "add-only" can trigger |
| `LEAVE_IT_SMALLER_MAX_RATIO` | `0.10` | deletions/additions below which the change reads as "add-only" |
| `LEAVE_IT_SMALLER_LARGE` | `400` | total changed lines from which the shown shape is flagged `large change` |
| `LEAVE_IT_SMALLER_MAX_NUDGES` | `2` | blocked stops per session |
| `LEAVE_IT_SMALLER_PROSE_SHARE` | `0.40` | share of a file's growth that is comments or docstrings from which it reads as prose-heavy |
| `LEAVE_IT_SMALLER_DISABLE` | unset | `1` silences both events |

Errors never fail a session: the hook exits 0 and logs to `~/.claude/leave-it-smaller/hook.log`.
