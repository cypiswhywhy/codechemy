# codechemy

Sharper [Claude Code](https://claude.com/claude-code) sessions: a plugin that holds every
session to the same engineering contract, plus skills for the work around the code —
shipping a PR, auditing a repo, auditing your own setup.

## Install

The plugin — one command, no clone:

```bash
claude plugin marketplace add cypiswhywhy/codechemy && claude plugin install engineering-practices@codechemy
```

The skills — not packaged yet, so they need a clone:

```bash
git clone https://github.com/cypiswhywhy/codechemy && cd codechemy
make install-skills     # copies claude-code/skills/* into ~/.claude/skills
make install-plugin     # installs the plugin, with this clone as the marketplace
```

Restart Claude Code afterwards so hooks and skills load.

Both targets copy: what is installed changes only when you run them again, never when the
working tree does. Re-run `make install-skills` to update the skills. `make install-plugin`
updates the plugin through `claude plugin update`, which is version-driven — bump `version`
in the plugin's `plugin.json` when you change it, or there is nothing for the update to do.

`make uninstall-skills` removes the skills this repo installed — and only those — and
`make uninstall-plugin` removes the plugin along with its marketplace entry.

## The plugin

[`engineering-practices`](claude-code/plugins/engineering-practices/README.md) — durable
defaults for every project: *leave the code smaller than you found it*, *small increments*,
*test-driven by default*.

| Piece | What it does |
|---|---|
| `SessionStart` hook | States the contract in every session |
| `Stop` hook | Nudges for a tidy pass when files only grew, or the change is large |
| `/maintenance-toolbox` | Records a project's dead-code, lint and test commands in its CLAUDE.md |

## The skills

| Skill | What it does |
|---|---|
| [`/push`](claude-code/skills/push/SKILL.md) | Pushes a branch, opens a PR, iterates on the Copilot review until green |
| [`/codebase-maintenance`](claude-code/skills/codebase-maintenance/SKILL.md) | Audits a repo across 11 quality dimensions and lands the fixes as small, revertible commits |
| [`/claude-customizations`](claude-code/skills/claude-customizations/SKILL.md) | Read-only audit of every Claude Code customization, CLI and Desktop, against a fresh install |
| [`/apply-increment`](claude-code/skills/apply-increment/SKILL.md) | Implements one OpenSpec task group as its own PR, then stops |
| [`/apply-all-increments`](claude-code/skills/apply-all-increments/SKILL.md) | Repeats that to main, archiving the change at the end |
| [docschemy](https://github.com/cypiswhywhy/docschemy) *(external)* | Generates and maintains project documentation |

## Also here

[`github-copilot/`](github-copilot/README.md) — setup notes for automated Copilot code
reviews, plus `copilot-instructions` templates to drop into a repository.

<details>
<summary><b>Prerequisites</b></summary>

`make install-skills` checks these first and prints what is missing, then installs anyway —
a missing command only disables the skills that call it. `make check` runs the same check on
its own and exits non-zero if anything is missing. The plugin targets are the exception: they
stop when `claude` is missing, since they have nothing to run without it.

| Command | Needed by | Get it |
|---|---|---|
| `git` | `/push`, `/codebase-maintenance`, both increment skills | https://git-scm.com/downloads |
| `gh` | `/push`, `/codebase-maintenance`, both increment skills | https://cli.github.com |
| `python3` | `/codebase-maintenance`, `/claude-customizations`, the plugin hooks | https://www.python.org/downloads |
| `openspec` | `/apply-increment`, `/apply-all-increments` | `npm install -g @fission-ai/openspec` |
| `claude` | the plugin targets | https://claude.com/claude-code |

</details>

<details>
<summary><b>Tests</b></summary>

```bash
python3 claude-code/plugins/engineering-practices/hooks/test_practices.py
python3 claude-code/plugins/engineering-practices/hooks/test_leave_it_smaller.py
python3 claude-code/skills/claude-customizations/scripts/test_inventory.py
```

</details>
