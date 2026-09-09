# codechemy

Assets for improving [Claude Code](https://claude.com/claude-code) workflows: a plugin that
gives every session the same engineering contract, skills for the jobs around the code
(shipping a PR, auditing a repo, auditing your own setup), and Copilot review setup notes.

Each folder has its own README with the details.

## Install

**The plugin** — one command, no clone:

```bash
claude plugin marketplace add cypiswhywhy/codechemy && claude plugin install engineering-practices@codechemy
```

Or paste this into any Claude Code session:

> Add the Claude Code marketplace `cypiswhywhy/codechemy` and install the
> `engineering-practices` plugin from it, then show me `claude plugin details
> engineering-practices`.

**The skills** — not in the plugin yet, so they need a clone:

```bash
git clone https://github.com/cypiswhywhy/codechemy && cd codechemy
make install-skills          # symlinks claude-code/skills/* into ~/.claude/skills
```

Restart Claude Code afterwards so hooks and skills load.

### Prerequisites

`make install-skills` checks these first and prints what is missing, then installs
anyway — a missing command only disables the skills that call it. `make check` runs
the same check on its own and exits non-zero if anything is missing.

| Command | Needed by | Get it |
|---|---|---|
| `git` | `/push`, `/codebase-maintenance`, both increment skills | https://git-scm.com/downloads |
| `gh` | `/push`, `/codebase-maintenance`, both increment skills | https://cli.github.com |
| `python3` | `/codebase-maintenance`, `/claude-customizations`, the plugin hooks | https://www.python.org/downloads |
| `openspec` | `/apply-increment`, `/apply-all-increments` | `npm install -g @fission-ai/openspec` |

## What's in here

### [`engineering-practices`](claude-code/plugins/engineering-practices/README.md) — the plugin

Durable defaults for every project: *leave the code smaller than you found it*, *small
increments*, *test-driven by default*.

| Piece | What it does |
|---|---|
| `SessionStart` hook | States the contract in every session |
| `Stop` hook | Nudges for a tidy pass when files only grew, or the change is large |
| `/maintenance-toolbox` | Records a project's dead-code, lint and test commands in its CLAUDE.md |

### [`claude-code/skills/`](claude-code/skills/index.md) — standalone skills

| Skill | What it does |
|---|---|
| [`/push`](claude-code/skills/push/SKILL.md) | Pushes a branch, opens a PR, iterates on the Copilot review until green |
| [`/codebase-maintenance`](claude-code/skills/codebase-maintenance/SKILL.md) | Audits a repo across 11 quality dimensions and lands the fixes as small, revertible commits |
| [`/claude-customizations`](claude-code/skills/claude-customizations/SKILL.md) | Read-only audit of every Claude Code customization, CLI and Desktop, against a fresh install |
| [`/apply-increment`](claude-code/skills/apply-increment/SKILL.md) | Implements one OpenSpec task group as its own PR, then stops |
| [`/apply-all-increments`](claude-code/skills/apply-all-increments/SKILL.md) | Repeats that to main, archiving the change at the end |
| [docschemy](https://github.com/cypiswhywhy/docschemy) *(external)* | Generates and maintains project documentation |

### [`github-copilot/`](github-copilot/README.md) — review setup

Setup notes for automated GitHub Copilot code reviews, plus `copilot-instructions`
templates to drop into a repository.

## Tests

```bash
python3 claude-code/plugins/engineering-practices/hooks/test_practices.py
python3 claude-code/plugins/engineering-practices/hooks/test_leave_it_smaller.py
python3 claude-code/skills/claude-customizations/scripts/test_inventory.py
```
