# codechemy

Sharper [Claude Code](https://claude.com/claude-code) sessions: a plugin that holds every
session to the same engineering contract, plus skills for the work around the code —
shipping a PR, auditing a repo, auditing your own setup.

## Install

Everything — the practices, the hooks and all six skills — ships in one plugin, so it is one
command and no clone:

```bash
claude plugin marketplace add cypiswhywhy/codechemy && claude plugin install engineering-practices@codechemy
```

Restart Claude Code afterwards so the hooks and skills load.

`claude plugin update engineering-practices` pulls new versions; it is version-driven, so a
change to this repo only reaches an install once `version` in the plugin's `plugin.json` goes
up. `claude plugin uninstall engineering-practices` removes the lot.

Working on the plugin? `make install-plugin` points the marketplace at your clone and installs
from it; `make uninstall-plugin` undoes that.

**Upgrading from a version before 2.0.0**, when the skills were copied into `~/.claude/skills`
by `make install-skills`: run `make migrate-skills` once. Those copies shadow the plugin's, so
they keep serving the old text until they are gone.

## The plugin

[`engineering-practices`](claude-code/plugins/engineering-practices/README.md) — durable
defaults for every project: *understand before you change*, *leave the code smaller than you
found it*, *reuse before adding*, *small increments*, *test-driven by default*, *correct by
construction*, *say less in the code*.

| Piece | What it does |
|---|---|
| `SessionStart` hook | States the contract in every session |
| `Stop` hook | Nudges for a tidy pass when files only grew, the change is large, no test moved with the code, or the summary states no diff shape |
| Eight skills | Shipped with the plugin — see the table below |

## The skills

All eight ship inside the plugin, so the install above is the only step.

| Skill | What it does |
|---|---|
| [`/frame`](claude-code/plugins/engineering-practices/skills/frame/SKILL.md) | One screen of design brief before implementing — problem, invariant, constraints, the approach chosen and one rejected — then one decision and into the code |
| [`/self-review`](claude-code/plugins/engineering-practices/skills/self-review/SKILL.md) | The mechanical pass over your own diff before anyone else reads it |
| [`/push`](claude-code/plugins/engineering-practices/skills/push/SKILL.md) | Runs `/self-review`, pushes, opens a PR, and iterates on the automated review until green — Copilot, or `/code-review` in a fresh-context subagent when Copilot is unavailable |
| [`/codebase-maintenance`](claude-code/plugins/engineering-practices/skills/codebase-maintenance/SKILL.md) | Audits a repo across 11 quality dimensions and lands the fixes as small, revertible commits |
| [`/claude-customizations`](claude-code/plugins/engineering-practices/skills/claude-customizations/SKILL.md) | Read-only audit of every Claude Code customization, CLI and Desktop, against a fresh install |
| [`/apply-increment`](claude-code/plugins/engineering-practices/skills/apply-increment/SKILL.md) | Implements one OpenSpec task group as its own PR, then stops |
| [`/apply-all-increments`](claude-code/plugins/engineering-practices/skills/apply-all-increments/SKILL.md) | Repeats that to main, archiving the change at the end |
| [`/maintenance-toolbox`](claude-code/plugins/engineering-practices/skills/maintenance-toolbox/SKILL.md) | Records a project's dead-code, lint and test commands in its CLAUDE.md |
| [docschemy](https://github.com/cypiswhywhy/docschemy) *(external)* | Generates and maintains project documentation |

## Also here

[`github-copilot/`](github-copilot/README.md) — setup notes for automated Copilot code
reviews, plus `copilot-instructions` templates to drop into a repository.

<details>
<summary><b>Prerequisites</b></summary>

`make install-plugin` checks these first and prints what is missing, then installs anyway —
a missing command only disables the skills that call it. `make check` runs the same check on
its own and exits non-zero if anything is missing. `claude` is the exception: the plugin
targets stop without it, since they have nothing to run.

| Command | Needed by | Get it |
|---|---|---|
| `git` | `/push`, `/codebase-maintenance`, both increment skills | https://git-scm.com/downloads |
| `gh` | `/push`, `/codebase-maintenance`, both increment skills | https://cli.github.com |
| `python3` | `/codebase-maintenance`, `/claude-customizations`, the plugin hooks | https://www.python.org/downloads |
| `openspec` | `/apply-increment`, `/apply-all-increments` | `npm install -g @fission-ai/openspec` |
| `claude` | installing and updating the plugin | https://claude.com/claude-code |

</details>

<details>
<summary><b>Tests</b></summary>

```bash
pytest
```

</details>
