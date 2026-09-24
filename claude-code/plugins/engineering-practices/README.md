# engineering-practices — durable defaults for Claude Code, in every project

A Claude Code plugin holding the practices I want a coding agent to follow in **every session,
in every project**. Three kinds of resource that combine into one behaviour:

| Directory | Loaded as | Role |
|---|---|---|
| `practices/*.md` | a `SessionStart` hook that prints them into the session's context (name order) | **the contract**: what the agent should do and why |
| `hooks/` | `hooks.json`, registered per event | **the nudge**: deterministic checks the agent cannot forget |
| `skills/<name>/` | `/<name>` in any session | **the know-how**: procedures the agent runs when asked or hinted |

Adding a practice is a new file in `practices/`; the hook picks it up. Today the plugin holds
seven practices, two hooks and eight skills, about six problems: agents start writing before
they have understood what is wanted; they add lines and rarely remove them, and turn a plan
into one thousand-line PR - or into six PRs none of which is useful on its own; they write a
near-copy of a helper instead of generalising the one that already exists; they leave errors
swallowed and input unchecked for the review to find; they document every line they write; and
they write the code first and the tests, if at all, afterwards.

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

- **05-understand-first.md**: the most expensive defect is a correct implementation of the
  wrong thing, and nothing downstream catches it. Restate the request as an outcome, name the
  invariant, read one existing example of the same kind of thing, name the two or three ways it
  can fail, ask only where two readings lead to different work - and run
  [`/frame`](skills/frame/SKILL.md) when the change touches a contract, crosses a module
  boundary or is hard to undo.
- **10-leave-it-smaller.md**: every change is also a maintenance pass over the code it
  touches. Tidy as you go, replace don't accumulate, delete don't deprecate, no defensive code
  the task does not need, prove then delete, a scope boundary, and the diff shape in every summary.
- **15-reuse-before-adding.md**: grep for the concept before writing a helper; the second call
  site is the threshold for extracting, not the third; generalise the existing code and put it
  where both callers already see it (base class, shared module, free function) rather than
  copying it; the extraction lands as its own `refactor:` commit, and is in scope even when it
  edits a file the task did not name.
- **20-small-increments.md**: name the landing points before writing, because a seam found in a
  finished diff is a file boundary; one test for each of them (merged on its own and stopped
  there, is someone better off with the default branch still green); commits are free and cut at
  every coherent step, a PR costs a review cycle and is cut only at a real seam; one piece of
  value lands whole at any size; the splits that only look like seams are named so they can be
  refused.
  The [`/apply-increment`](skills/apply-increment/SKILL.md) and
  [`/apply-all-increments`](skills/apply-all-increments/SKILL.md) skills carry this out for an
  OpenSpec project.
- **30-test-driven.md**: red-green-refactor whenever a change alters behaviour and the project
  has a test harness. Failing test first and seen failing, smallest code to green, refactor on
  green; bug fixes start with a reproducing test; a red test means root-cause the code, and the test
  changes only once the logic under it is shown correct; not
  applicable to docs, config, one-off scripts and declared spikes, and the summary says so.
- **35-correct-by-construction.md**: the defects the review loop and the audit find one cycle
  at a time, written correctly the first time instead. Validate where data crosses into your
  code and trust it inside; propagate errors with context and never swallow one; name shared
  state before creating it; make anything reachable twice safe twice; release on the error path;
  keep untrusted input out of interpreters and credentials out of logs.
- **40-say-less.md**: comments carry the *why* only; one-line docstrings stating the contract,
  none at all where the name and signature already say it; length only for a reason outside the
  code; no change narration, `TODO`s or commented-out code; match the density of the file.

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
| the change gained ≥ 40 lines and lost < 10 % of that | **block once** with the diff shape and three questions: does it duplicate what already exists, did it supersede a path still in the tree, is there anything dead in what it touched |
| total change ≥ 400 lines | **block once per session** asking which landing points were named up front, and refusing a retroactive slice by file or layer as a split |
| source files changed, no test changed, and the repo has tests | **block once per session** asking which behaviour changed and what now covers it - or to say that none did, with the test command and its result |
| a source file grew ≥ 20 lines, ≥ 40 % of them comments or docstrings, and 15 points past the file's own density | **block once per session** naming the files and asking for the pass "Say less in the code" describes: delete comments that narrate or restate, cut docstrings to the contract |
| the change is ≥ 40 lines and the last message states no `+N / -M` | **block once per session** asking for the diff shape and the test result the contract requires |
| otherwise, when the shape changed since the last stop | one-line `systemMessage` with `+N / -M across F files` |

The summary check reads the session transcript for the message the agent is about to hand back; when
there is no transcript, or its format is not the one expected, the check passes rather than
blocking. Bounded by construction: never while the agent is already continuing because of a stop
hook, never twice for the same diff, each check at most once per session, at most two blocks per
session in all; after that the smell is still shown to you but the agent is not interrupted. `session-start` tells the agent to offer
`/maintenance-toolbox` once when the repository's `CLAUDE.md` has no `## Maintenance toolbox`.

| Variable | Default | Meaning |
|---|---|---|
| `LEAVE_IT_SMALLER_MIN_ADDED` | `40` | added lines before "add-only" can trigger |
| `LEAVE_IT_SMALLER_MAX_RATIO` | `0.10` | deletions/additions below which the change reads as "add-only" |
| `LEAVE_IT_SMALLER_LARGE` | `400` | total changed lines from which to look for a shippable increment |
| `LEAVE_IT_SMALLER_MAX_NUDGES` | `2` | blocked stops per session |
| `LEAVE_IT_SMALLER_PROSE_SHARE` | `0.40` | share of a file's growth that is comments or docstrings from which it reads as prose-heavy |
| `LEAVE_IT_SMALLER_DISABLE` | unset | `1` silences both events |

### Skills (`skills/`)

Eight, all installed with the plugin.

| Skill | What it does |
|---|---|
| [`/frame`](skills/frame/SKILL.md) | One screen of design brief and plan - problem, what was assumed, invariant, constraints cited from the repo, the approach chosen and one rejected with its reason, blast radius, then the landing points with the test that proves each and how it can fail - then one decision and straight into the code. Says up front whether it frames at all. Refuses when the change is small enough to just write, and defers to `/opsx:propose` where the repo uses OpenSpec |
| [`/self-review`](skills/self-review/SKILL.md) | The mechanical pass over your own diff before anyone else reads it: symbols that do not exist, anchors that drifted, absolutes with a counterexample, claims the code cannot observe, duplication you just added, error paths, tests asserting a proxy |
| [`/push`](skills/push/SKILL.md) | Branch to merge-ready PR: self-review, push, PR, then the automated review loop until green, capped at three cycles counted from the branch - Copilot, or one pass of `/code-review` in a fresh-context subagent when Copilot is unavailable |
| [`/codebase-maintenance`](skills/codebase-maintenance/SKILL.md) | Audits a repo across 11 quality dimensions and lands the fixes as small, verified commits, through to a merge-ready PR |
| [`/maintenance-toolbox`](skills/maintenance-toolbox/SKILL.md) | Records a project's dead-code, unused-dependency, lint and test commands in its CLAUDE.md, so deletions can be proven |
| [`/claude-customizations`](skills/claude-customizations/SKILL.md) | Read-only audit of every Claude Code customization, CLI and Desktop, against a fresh install |
| [`/apply-increment`](skills/apply-increment/SKILL.md) | Implements one OpenSpec task group as its own PR, then stops |
| [`/apply-all-increments`](skills/apply-all-increments/SKILL.md) | Walks a change to main one increment per session, archiving the change at the end |

`/apply-increment` and `/apply-all-increments` need the `openspec` CLI, and
`/codebase-maintenance` and `/claude-customizations` need `python3`; a missing command disables
only the skill that calls it.

### Skill: `/maintenance-toolbox` in detail

Deletion needs global knowledge the agent lacks: which command lists dead code, unused
dependencies, unused imports, and runs the tests. The skill detects the stack, finds what is
configured (or proposes `vulture`/`deptry`/`ruff`, `knip`, `staticcheck`, `cargo machete`, ...),
asks the user one question about adding what is missing, verifies each command runs, and
writes a five-line `## Maintenance toolbox` section to the project's `CLAUDE.md`, where the
contract tells the agent to look before deleting. Declining writes
`<!-- maintenance-toolbox: none -->` so the hint stops. It records; `/codebase-maintenance` fixes.

## Tests

```bash
pytest
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
- **Why thresholds, and why new files count.** Zero removals in a 15-line addition is normal;
  in a 200-line change it is the smell this exists to catch - and a new module is exactly where
  a duplicated helper or a superseded path hides, so it is measured like any other file. Defaults are conservative and env-tunable.
- **Stdlib only.** `leave_it_smaller.py` exits 0 on any error and logs under
  `~/.claude/leave-it-smaller/hook.log`, so a stop is never blocked by a bug in it.
