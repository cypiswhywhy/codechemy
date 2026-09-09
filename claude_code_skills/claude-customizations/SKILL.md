---
name: claude-customizations
description: Audit every Claude Code customization on this machine, in both the CLI and the Claude Desktop app, and report exactly how the environment differs from a fresh install. Has a short "implicit" view limited to what shapes a session without the user invoking it (hooks, CLAUDE.md, model-invocable skills, agents, plugins, MCP servers, permissions, env). Runs a read-only inventory script over the user config dir, the global state file, managed settings, environment variables, the Desktop app's config, and the current project, then explains each item and flags anomalies (broken skill links, unregistered hook scripts, plugins enabled but not installed, leftover files). Use when the user says "/claude-customizations", "what have I customized in Claude Code", "audit my Claude setup", "diff my setup against a clean install", "what's in my ~/.claude", "what affects my sessions without me asking", "what runs on its own in Claude Code", or before cleaning up or migrating a Claude Code environment. Changes nothing.
---

# Claude Code customizations audit

Show the user everything that makes their Claude Code differ from a clean install, in
both contexts it runs in: the `claude` CLI and Claude Code inside the Claude Desktop app.
Both read the same `~/.claude` config dir and `~/.claude.json`, so the user scope is
shared; the Desktop app adds a config dir of its own. This skill is **read-only**: it
never edits, deletes or moves anything. Cleanup is a separate, user-approved step.

## Step 1 — Run the inventory

```bash
python3 <skill-dir>/scripts/inventory.py                # everything, grouped by effect, project scope = cwd
python3 <skill-dir>/scripts/inventory.py --implicit     # only what acts on a session by itself
python3 <skill-dir>/scripts/inventory.py --by-location  # grouped by where each item lives instead
python3 <skill-dir>/scripts/inventory.py --json         # same data for programmatic use
```

**Pick the view from the ask.** Use `--implicit` when the user asks what affects their
sessions, what runs on its own, what Claude "sees" or "does without asking", or for a
short or quick view; also when the skill is invoked as `/claude-customizations implicit`
(or `quick`, `short`). Use the full view for "everything", "what have I customized",
cleanup and migration. When unsure, run the implicit view first and offer the full one.

The implicit view keeps: instructions (`CLAUDE.md`, rules, managed settings), registered
hooks, skills and commands the model may invoke on its own, agents, enabled plugins, MCP
servers, permissions, behaviour-affecting settings, env vars, scheduled tasks. It drops
UI preferences, keybindings, themes, marketplaces, disabled plugins, unregistered hook
scripts and leftover files. A skill counts as model-invocable unless its frontmatter has
`disable-model-invocation: true`; that is Claude Code's own rule, so a skill the user
thinks of as "mine to run" still appears until it is marked. If the user is surprised by
one, say that, and offer to mark it (in the skill's own repo, as a separate change).

**Defaults.** Settings values, `~/.claude.json` preferences and env vars carry a dim
`default: …` note when the official docs state one (in `--json`: the `defaults`,
`preference_defaults` and `default` fields). An env var with no documented effect shows
`default: unset`, which is literally true on a fresh install. A value that merely restates
the default is marked `(= default)`: it changes nothing, so list it among the cleanup
candidates. Items with no note have no documented default; say so if asked rather than
inventing one.

`<skill-dir>` is the directory holding this SKILL.md (resolve the symlink if
`~/.claude/skills/claude-customizations` is one). Pass `--project DIR` when the user
asks about a project other than the cwd. The script is stdlib-only and redacts anything
that looks like a credential; never paste raw config files into the conversation to
"double-check" it.

**Default layout: by effect.** One line of versions (with a warning when Desktop bundles
an older Claude Code than the CLI), then six sections, each answering one question. The
source path is a dim column on every row, so "where do I change this" is still answered.
Everything listed is absent on a fresh install.

| Section | Question | What lands there |
|---|---|---|
| Instructions | What is every session told? | user, managed and project `CLAUDE.md` / `AGENTS.md` (headings, managed blocks, `@includes`), rules. Says `none` for a missing managed or project file. |
| Behaviour | How does the agent run? | model, effort, permissions and other behaviour settings from every settings file, managed policy, env vars with source and default, per-project allow-lists and MCP toggles remembered in `~/.claude.json`, Desktop's encrypted env vars (presence only). |
| Automation | What runs without asking? | hooks from every settings file, scheduled tasks, skills and commands the model may invoke on its own, agents. |
| Tools | What can the agent reach? | plugins with their marketplace, MCP servers from `~/.claude.json`, `.mcp.json`, Claude Desktop and managed policy, Desktop extensions. Says `none` when there are no MCP servers. |
| Interface | What only changes the UI? | `tui`, status line and other display settings, `~/.claude.json` preferences, keybindings, themes, workflows, skills marked user-invoked only, Desktop preferences (count and sample). |
| Leftovers | What owns nothing? | unregistered hook scripts, broken skill links, `settings.json` backups (one line), unrecognized files in the config dir, remembered projects whose directory is gone. A file whose name matches a managed block or hook script is attributed ("owned by the X bundle") instead of flagged. |

`--implicit` prints Instructions, Behaviour, Automation and Tools only, on top of the item
filter described above.

**`--by-location`** keeps the former layout: Versions, User scope (`~/.claude` and
`~/.claude.json`), Managed scope, Environment variables, Claude Desktop, Project scope,
in override order. Use it when the user asks about a place ("what is in my `~/.claude`",
"what does this project add") or is cleaning up or migrating a machine, where seeing
one directory at a time is what matters. The JSON output is the same for both layouts.

## Step 2 — Interpret, don't just relay

The script gives facts. Your job is the reading a colleague would give:

1. **Group by intent, not by file.** Tell the user what each cluster does in a sentence:
   "telemetry to a local OTLP collector", "the engineering-practices bundle (managed
   CLAUDE.md block + two hooks + two skills)", "docschemy docs skills linked from a
   checkout". Infer bundles from managed-block names, hook script names, state files and
   symlink targets.
2. **Flag anomalies** the script marks in capitals or lists under `unrecognized`, and
   say what each means:
   - `BROKEN LINK` skill — the source checkout moved or was deleted; the skill no longer loads.
   - hook script `NOT registered` — a file in `hooks/` that no `settings.json` event runs; left over from an uninstall, or an install that never finished.
   - plugin `ENABLED BUT NOT INSTALLED` or `files missing` — `settings.json` names it but the plugin cache does not have it.
   - `unrecognized` entries — anything in the config dir that is neither a known customization nor known runtime state: `.bak` files, per-tool state dirs, logs, env files from older installers. Say which installer likely owns each (match names against the hooks, managed blocks and state files you saw) and whether it still has an owner.
   - Desktop bundles an **older Claude Code than the CLI** — worth a line, since behaviour can differ between the two contexts.
   - a `~/.claude.json` project entry for a path that no longer exists.
3. **Separate the two contexts.** State plainly what applies to both CLI and Desktop
   (everything in user scope and managed scope) and what is Desktop-only (its MCP
   servers, extensions, encrypted env vars, preferences). If the user asked about one
   context only, still run the whole script but lead with that context.
4. **Note what the script cannot see** when relevant: Desktop's Claude Code env vars are
   encrypted; MCP servers provided by the claude.ai connector directory live server-side
   and are not in any local file; `~/.claude.json` preferences beyond the known set are
   treated as runtime state.

## Step 3 — Report

Lead with one or two sentences: how far this machine is from a clean install, and the
single most important anomaly if there is one. Then the grouped inventory as a short
list per section, anomalies bolded at the top of their section, skipping sections that
are empty. Keep values out of prose; a path, count or version goes on its own line.

End with the cleanup candidates as a bulleted list the user can say yes or no to, one
line each with the reason ("6 settings.json backups from earlier installers, newest
already superseded"). **Do not perform any of them** in this run, even if they look
safe; the user picks, and removal happens in a follow-up with its own confirmation.

## Notes

- Desktop-specific file locations (`claude_desktop_config.json`, `Claude Extensions/`,
  `ccd-environment-config.json`) are observed, not documented by Anthropic; if the
  Desktop section comes back empty on a machine that clearly runs Desktop, check the
  app's config dir by hand and report the discrepancy rather than guessing.
- Tests: `python3 <skill-dir>/scripts/test_inventory.py`.
