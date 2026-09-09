# codechemy

Assets for improving Claude Code workflows. Each folder has its own README / docs
with setup details.

## Install

The [engineering-practices](claude-code/plugins/engineering-practices/README.md) plugin, in one
command — no clone needed:

```bash
claude plugin marketplace add cypiswhywhy/codechemy && claude plugin install engineering-practices@codechemy
```

Or paste this into any Claude Code session:

> Add the Claude Code marketplace `cypiswhywhy/codechemy` and install the
> `engineering-practices` plugin from it, then show me `claude plugin details
> engineering-practices`.

The skills in `claude-code/skills/` are not in the plugin yet; they install from a clone:

```bash
make install-skills          # symlink claude-code/skills/* into ~/.claude/skills
```

## Contents

- **[claude-code/plugins/engineering-practices/](claude-code/plugins/engineering-practices/README.md)** — durable defaults for Claude Code in every project: a `SessionStart` hook that states the contract (leave the code smaller than you found it; small increments; test-driven by default), a `Stop` hook that nudges for a tidy pass when existing files only grew or the change is large, and three skills: `/maintenance-toolbox` (record a project's dead-code/lint/test commands), `/apply-increment` (implement one OpenSpec task group per PR) and `/apply-all-increments` (loop that to main).
- **[claude-code/skills/](claude-code/skills/index.md)** — Claude Code skills:
  - [push](claude-code/skills/push/SKILL.md) — `/push`: pushes a branch, opens a PR, and iterates on the GitHub Copilot review loop until green.
  - [codebase-maintenance](claude-code/skills/codebase-maintenance/SKILL.md) — `/codebase-maintenance`: audits an existing repo across 11 quality dimensions and applies the findings as small, verified, independently revertible commits.
  - [claude-customizations](claude-code/skills/claude-customizations/SKILL.md) — `/claude-customizations`: read-only audit of every Claude Code customization, CLI and Desktop, against a fresh install.
  - [docschemy](https://github.com/cypiswhywhy/docschemy) (external) — commands and skills for generating and maintaining project documentation.
- **[github-copilot/](github-copilot/README.md)** — setup notes for automated GitHub Copilot code reviews, plus `copilot-instructions` templates for repositories.

## Tests

```bash
python3 claude-code/plugins/engineering-practices/hooks/test_practices.py
python3 claude-code/plugins/engineering-practices/hooks/test_leave_it_smaller.py
python3 claude-code/skills/claude-customizations/scripts/test_inventory.py
```
