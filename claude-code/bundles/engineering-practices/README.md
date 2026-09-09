# engineering-practices — durable defaults for Claude Code, in every project

A bundle of the practices I want a coding agent to follow in **every session, in every
project**, installed with one command. It is **not a Claude Code plugin**: a plugin can carry
hooks and skills but cannot write to your global `~/.claude/CLAUDE.md`, and the instruction
layer is the part that carries the *why*. So the bundle is three kinds of resource that
combine into one behaviour, and a stdlib installer that is generic over them:

| Directory | Becomes | Role |
|---|---|---|
| `practices/*.md` | one managed block in `~/.claude/CLAUDE.md` (files concatenated in name order) | **the contract**: what the agent should do and why |
| `hooks/<name>/` (`hook.json` + script + tests) | a script in `~/.claude/hooks/`, registered in `~/.claude/settings.json` per event | **the nudge**: deterministic checks the agent cannot forget |
| `skills/<name>/` | a copy in `~/.claude/skills/<name>/` | **the know-how**: procedures the agent runs when asked or hinted |
| `VERSION` | the version stamp in the block header and in `~/.claude/engineering-practices.json` | tells a user what they have |

Adding a practice is a new file; the installer picks it up. Today the bundle holds three practices,
one hook and three skills, about two problems: agents add lines and rarely remove them, and turn a
plan into one thousand-line PR; and they write the code first and the tests, if at all, afterwards.

## Install

From a clone of this repository:

```bash
make install-engineering-practices      # from the repository root
make uninstall-engineering-practices    # removes everything it added
```

Without `make`: `python3 engineering-practices/install.py [--uninstall]`.

Prefer to let Claude do it? Paste this into any Claude Code session:

> Clone `git@github.com:cypiswhywhy/codechemy.git` (or `git pull` if I already have it), run `make install-engineering-practices` from its root, and show me the output.

Requirements: Python 3.9+, `git`, macOS or Linux. Restart Claude Code (or run `/hooks`) so
the hooks load. Re-running is safe: the managed block, hook scripts and skill copies are
replaced in place, other content in `CLAUDE.md` and `settings.json` is untouched,
`settings.json` is backed up first, and the self-test runs at the end.

## Updating and versions

**Everything installed is a copy. `git pull` changes nothing in your environment**; only the
installer applies a new version:

```bash
cd codechemy && git pull && make install-engineering-practices
make status-engineering-practices     # what is installed vs what the checkout offers
```

The bundle version lives in `VERSION` (semver, bumped with every change to `practices/`,
`hooks/` or `skills/`). The installer stamps it into the managed block's header
(`<!-- engineering-practices:begin v0.1.0 ... -->`) and records it, with the bundle commit
and the list of installed practices, hooks and skills, in `~/.claude/engineering-practices.json`.
`--status` compares that record with the checkout and tells you when to reinstall. The record
is also how the installer knows which `~/.claude/skills/<name>/` directories are its own:
a directory it did not create is never overwritten or removed.

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

### Hook: `leave-it-smaller` (`hooks/leave-it-smaller/`)

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
python3 engineering-practices/test_install.py
python3 engineering-practices/hooks/leave-it-smaller/test_hook.py
```

Throwaway git repositories and config dirs; the hook is driven the way Claude Code drives it
(JSON on stdin). The installer runs both suites after installing.

## Adding a practice, hook or skill

- **Practice**: add `practices/NN-<topic>.md` with a single `#` heading; keep it to rules the
  agent can check itself against, with the reason in one clause. Re-run the installer.
- **Hook**: add `hooks/<name>/hook.json` (`script`, `events` mapping event → subcommand,
  optional `timeout`), the script (stdlib, exit 0 on any error, log under
  `~/.claude/<name>/`), and a `test_*.py`. Re-run the installer.
- **Skill**: add `skills/<name>/SKILL.md` with `name` equal to the directory. Re-run the installer.
- Bump `VERSION` in the same change; the installer test insists on semver.

## Design notes

- **Why not a plugin.** Plugins are the right vehicle for hooks and skills alone, and the
  `hooks/` + `skills/` halves could become one later. The contract has to live in `CLAUDE.md`
  (a plugin cannot write there, and a SessionStart hook that prints it would re-spend the tokens
  every session and rank below the system prompt), so the bundle owns all three and installs
  them the same way.
- **Why all three layers.** A CLAUDE.md rule alone is forgotten by turn 40; a hook alone can
  measure but not explain; a skill alone is never invoked. The contract says what, the hook keeps
  it visible late in a session, the skills make the expensive part (proving a deletion, splitting
  a plan) cheap enough to happen.
- **Why the hook blocks instead of only reporting.** A `systemMessage` is seen by the user; a
  `decision: block` with a `reason` is seen by the agent and acted on before it hands back.
- **Why it is bounded.** An unbounded nudge becomes noise the agent learns to justify away.
- **Why thresholds.** Zero removals in a 15-line addition is normal; in a 200-line change to
  existing files it is the smell this exists to catch. Defaults are conservative and env-tunable.
- **Stdlib only, never fails the session.** Hooks exit 0 on any error and log under
  `~/.claude/<hook-name>/hook.log`.
