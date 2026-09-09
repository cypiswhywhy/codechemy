# codechemy

Assets for improving Claude Code workflows. Each folder has its own README / docs
with setup details.

## Install

```bash
make install-skills                  # symlink claude-code/skills/* into ~/.claude/skills
make install-engineering-practices   # CLAUDE.md block + hook + skills (see its README)
make status-engineering-practices    # what is installed vs what this checkout offers
make uninstall-engineering-practices
```

## Contents

- **[claude-code/skills/](claude-code/skills/index.md)** — Claude Code skills:
  - [push](claude-code/skills/push/SKILL.md) — `/push`: pushes a branch, opens a PR, and iterates on the GitHub Copilot review loop until green.
  - [codebase-maintenance](claude-code/skills/codebase-maintenance/SKILL.md) — `/codebase-maintenance`: audits an existing repo across 11 quality dimensions and applies the findings as small, verified, independently revertible commits.
  - [claude-customizations](claude-code/skills/claude-customizations/SKILL.md) — `/claude-customizations`: read-only audit of every Claude Code customization, CLI and Desktop, against a fresh install.
  - [docschemy](https://github.com/cypiswhywhy/docschemy) (external) — commands and skills for generating and maintaining project documentation.
- **[claude-code/bundles/engineering-practices/](claude-code/bundles/engineering-practices/README.md)** — durable defaults for Claude Code in every project, installed with `make install-engineering-practices`: a managed `~/.claude/CLAUDE.md` block (leave the code smaller than you found it; small increments; test-driven by default), a `Stop` hook that nudges for a tidy pass when existing files only grew or the change is large, and three skills: `/maintenance-toolbox` (record a project's dead-code/lint/test commands), `/apply-increment` (implement one OpenSpec task group per PR) and `/apply-all-increments` (loop that to main).
- **[claude-code/hooks/vibe-diary-hook/](claude-code/hooks/vibe-diary-hook/README.md)** — a `SessionEnd` hook that logs each Claude Code session (times, model, token usage, cost, auto-summary) to a Confluence page, grouped by git branch.
- **[claude-code/plugins/mcp-audit-plugin/](claude-code/plugins/mcp-audit-plugin/README.md)** — a Claude Code plugin that keeps a durable audit log of every MCP tool call from selected servers, for reviewing whether an MCP was invoked when it shouldn't have been.
- **[github-copilot/](github-copilot/README.md)** — setup notes for automated GitHub Copilot code reviews, plus `copilot-instructions` templates for repositories.

## Tests

```bash
python3 claude-code/bundles/engineering-practices/test_install.py
python3 claude-code/bundles/engineering-practices/hooks/leave-it-smaller/test_hook.py
python3 claude-code/skills/claude-customizations/scripts/test_inventory.py
python3 claude-code/hooks/vibe-diary-hook/test_hook.py
```
