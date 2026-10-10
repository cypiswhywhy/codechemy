# 0001. Ship as a plugin, with the contract printed by a SessionStart hook

- **Status**: Accepted
- **Date**: 2026-09-09

## Context
Recorded retroactively from commit `2794bf4` ("convert bundle to a plugin") and the plugin
README's design notes. The practices, hooks and skills were installed by cloning the repository
and running a `make` target backed by a roughly 500-line installer, which had to be re-run after
every `git pull`. A plugin cannot write to `~/.claude/CLAUDE.md`, where a global contract would
normally live.

## Decision
Package everything as one Claude Code plugin, `engineering-practices`, listed by a marketplace
in this repository. Deliver the contract through a `SessionStart` hook that prints
`practices/*.md` into the session.

## Consequences
- Install, update and per-project enabling come from `claude plugin` and `/plugin`; no clone.
- The contract costs the same tokens as a global `CLAUDE.md`, which is also injected every session.
- Updates reach users only when the plugin's `version` goes up.
- Skills copied into `~/.claude/skills` by older installs shadow the plugin's, hence
  `make migrate-skills`.
