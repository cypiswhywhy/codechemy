# engineering-practices — durable defaults for Claude Code, in every project

A Claude Code plugin holding the practices I want a coding agent to follow in **every session,
in every project**. Three kinds of resource that combine into one behaviour:

| Directory | Loaded as | Role |
|---|---|---|
| `practices/*.md` | a `SessionStart` hook that prints them into the session's context (name order) | **the contract**: what the agent should do and why |
| `hooks/` | `hooks.json`, registered per event | **the nudge**: deterministic checks the agent cannot forget |
| `skills/<name>/` | `/<name>` in any session | **the know-how**: procedures the agent runs when asked or hinted |

Adding a practice is a new file in `practices/`; the hook picks it up. Today the plugin holds
three practices, two hooks and three skills, about two problems: agents add lines and rarely
remove them, and turn a plan into one thousand-line PR; and they write the code first and the
tests, if at all, afterwards.

## Install

One command, no clone:

```bash
claude plugin marketplace add cypiswhywhy/codechemy && claude plugin install engineering-practices@codechemy
```

Or paste this into any Claude Code session:

> Add the Claude Code marketplace `cypiswhywhy/codechemy` and install the
> `engineering-practices` plugin from it, then show me `claude plugin details
> engineering-practices`.

Restart Claude Code (or start a new session) afterwards so the hooks load. Requires stdlib
Python 3.9+ and `git`, on macOS or Linux.

```bash
claude plugin marketplace update codechemy   # pull new versions
claude plugin update engineering-practices
claude plugin uninstall engineering-practices
```

`/plugin` does the same interactively, and enables or disables the plugin per project.

**Working on the plugin?** Point the marketplace at your clone instead
(`claude plugin marketplace add /path/to/codechemy`); `marketplace update` then picks up your
edits, and the hooks run straight from the working tree. A marketplace name holds one source,
so switching between the clone and GitHub means `claude plugin marketplace remove codechemy`
first — otherwise the add is refused for a source that differs from the declared one.

**A whole repository at once**: commit this to the project's `.claude/settings.json` and every
clone of it gets the plugin with no command at all.

```json
{
  "extraKnownMarketplaces": {
    "codechemy": {"source": {"source": "github", "repo": "cypiswhywhy/codechemy"}}
  },
  "enabledPlugins": {"engineering-practices@codechemy": true}
}
```

## What is in it

### Practices (`practices/`)

- **10-leave-it-smaller.md**: every change is also a maintenance pass over the code it
  touches. Tidy as you go, replace don't accumulate, delete don't deprecate, no defensive code
  the task does not need, prove then delete, a scope boundary, and the diff shape in every summary.
- **20-small-increments.md**: refactor first, then feature, then follow-ups; cleanup in its own
  commits; about 400 changed lines is where you land what is complete; one task group per PR.
- **30-test-driven.md**: red-green-refactor whenever a change alters behaviour and the project
  has a test harness. Failing test first and seen failing, smallest code to green, refactor on
  green; bug fixes start with a reproducing test; a red test means root-cause the code, and the test
  changes only once the logic under it is shown correct; not
  applicable to docs, config, one-off scripts and declared spikes, and the summary says so.

### Hook: `practices` (`hooks/practices.py`)

`SessionStart`. Concatenates `practices/*.md` in name order behind one line saying these are
standing instructions that override conflicting defaults, and prints them; Claude Code adds
stdout to the session's context. Editing a practice takes effect in the next session.

### Hook: `leave-it-smaller` (`hooks/leave_it_smaller.py`)

One script, two events. `stop` measures the whole pending change (branch vs merge-base with
`main`/`master` plus working tree; on the default branch, unpushed commits plus working tree;
untracked files count as new, binaries are ignored) and acts per stop:

| Condition (defaults) | Action |
|---|---|
| no repository or no change | silent |
| existing files gained ≥ 40 lines and lost < 10 % of that | **block once** with the diff shape and a tidy-pass request |
| total change ≥ 400 lines | **block once per session** asking to land what is complete as an increment |
| otherwise, when the shape changed since the last stop | one-line `systemMessage` with `+N / -M across F files` |

Bounded by construction: never while the agent is already continuing because of a stop hook,
never twice for the same diff, at most two blocks per session; after that the smell is still
shown to you but the agent is not interrupted. `session-start` tells the agent to offer
`/maintenance-toolbox` once when the repository's `CLAUDE.md` has no `## Maintenance toolbox`.

| Variable | Default | Meaning |
|---|---|---|
| `LEAVE_IT_SMALLER_MIN_ADDED` | `40` | added lines in existing files before "growth" can trigger |
| `LEAVE_IT_SMALLER_MAX_RATIO` | `0.10` | deletions/additions below which growth is "add-only" |
| `LEAVE_IT_SMALLER_LARGE` | `400` | total changed lines that read as "large; land an increment" |
| `LEAVE_IT_SMALLER_MAX_NUDGES` | `2` | blocked stops per session |
| `LEAVE_IT_SMALLER_DISABLE` | unset | `1` silences both events |

### Skill: `/maintenance-toolbox`

Deletion needs global knowledge the agent lacks: which command lists dead code, unused
dependencies, unused imports, and runs the tests. The skill detects the stack, finds what is
configured (or proposes `vulture`/`deptry`/`ruff`, `knip`, `staticcheck`, `cargo machete`, ...),
asks the user one question about adding what is missing, verifies each command runs, and
writes a five-line `## Maintenance toolbox` section to the project's `CLAUDE.md`, where the
contract tells the agent to look before deleting. Declining writes
`<!-- maintenance-toolbox: none -->` so the hint stops. It records; `/codebase-maintenance` fixes.

### Skill: `/apply-increment`

`/opsx:apply` walks a whole OpenSpec task list in one run. This skill implements **one task
group** (`## N.` heading in `tasks.md`), lands it as its own PR via `/push` (or `gh`), and stops;
run it again after the merge. On first use in a project it offers, once, to seed
`openspec/config.yaml` with a `rules.tasks` entry (group tasks into PR-sized increments at
propose time) and an `operations.apply.guidance` entry (one group per run) that OpenSpec feeds
to the vendor `/opsx:propose` and `/opsx:apply` commands too, so the increment behaviour holds
even when someone uses those directly.

### Skill: `/apply-all-increments`

The loop around `/apply-increment`. It revalidates the change against today's main (artifacts
complete, named files and dependencies still there, groups still PR-sized), then for every
remaining group runs `/apply-increment`, lets `/push` take the PR to green, asks the user to merge
and continues from a fresh main. When the last group has landed it archives the change through
`/opsx:archive` on its own PR and reports every increment with its PR and diff shape. The user's
only manual step is the merge; state lives in `tasks.md` and on GitHub, so an interrupted run is
resumed by running it again.

## Tests

```bash
python3 hooks/test_practices.py
python3 hooks/test_leave_it_smaller.py
```

Throwaway git repositories and config dirs; each hook is driven the way Claude Code drives it
(JSON on stdin).

## Adding a practice, hook or skill

- **Practice**: add `practices/NN-<topic>.md` with a single `#` heading; keep it to rules the
  agent can check itself against, with the reason in one clause.
- **Hook**: add the script to `hooks/` (stdlib, log under `~/.claude/<name>/`), register it in
  `hooks/hooks.json` with `${CLAUDE_PLUGIN_ROOT}` in the command, and add a `test_*.py`.
- **Skill**: add `skills/<name>/SKILL.md` with `name` equal to the directory.
- Bump `version` in `.claude-plugin/plugin.json` in the same change.

## Design notes

- **Why a plugin, and why the contract is a hook.** A plugin cannot write to
  `~/.claude/CLAUDE.md`, so the contract is printed by a `SessionStart` hook instead. That costs
  the same tokens (a global `CLAUDE.md` is injected every session too) and buys `/plugin install`,
  `/plugin update` and per-project enabling in place of a clone, a `make` target and a 500-line
  installer that had to be re-run after every `git pull`.
- **Why all three layers.** A rule alone is forgotten by turn 40; a hook alone can measure but
  not explain; a skill alone is never invoked. The contract says what, the `leave-it-smaller`
  hook keeps it visible late in a session, the skills make the expensive part (proving a
  deletion, splitting a plan) cheap enough to happen.
- **Why the hook blocks instead of only reporting.** A `systemMessage` is seen by the user; a
  `decision: block` with a `reason` is seen by the agent and acted on before it hands back.
- **Why it is bounded.** An unbounded nudge becomes noise the agent learns to justify away.
- **Why thresholds.** Zero removals in a 15-line addition is normal; in a 200-line change to
  existing files it is the smell this exists to catch. Defaults are conservative and env-tunable.
- **Stdlib only.** `leave_it_smaller.py` exits 0 on any error and logs under
  `~/.claude/leave-it-smaller/hook.log`, so a stop is never blocked by a bug in it.
