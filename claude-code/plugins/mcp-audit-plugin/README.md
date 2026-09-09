# mcp-audit

A Claude Code **plugin** that keeps a deterministic, durable log of every MCP
tool call from the servers *you* choose to audit — so you can review whether an
MCP was invoked when it shouldn't have been, and (later) flag when it wasn't
invoked but should have been.

It captures calls at the source with `PreToolUse` / `PostToolUse` hooks (no
model scanning history), writes one JSONL line per event, and ships a script to
push rows into a shared Confluence table your whole team can read.

## What gets logged

For each matching call, a `pre` line (durable, written before the call) and a
`post` line (outcome + duration) are appended to
`~/.claude/mcp-audit/mcp-invocations.jsonl`:

- `ts` (UTC), `user`, `host`, `session_id`, `tool_use_id`, `cwd`
- `server` (derived), `tool_name`
- `tool_input` (truncated to `truncate_bytes`, default 2 KB)
- `status` (success/error) and `duration_ms` on the `post` line

`pre` and `post` are correlated by `tool_use_id`, so duration and outcome pair
correctly even under concurrent calls.

## Install

**1. Load the plugin**

For quick use, point Claude Code at this directory:

```bash
claude --plugin-dir /path/to/mcp-audit-plugin
```

For a permanent, team-wide install, publish it to your Claude Code plugin
marketplace and have teammates install `mcp-audit` from there.

**2. Choose which servers to audit** (nothing is logged until you do)

```bash
bash /path/to/mcp-audit-plugin/scripts/init-config.sh --servers=cookiev2,atlassian,asana
```

This writes `~/.claude/mcp-audit/config.json`. A server name is the middle
token of its tool ids — `mcp__<server>__<tool>`. Edit the file anytime to change
the list; matching is anchored on the full `mcp__<server>__` prefix, so
`asana` never accidentally matches `asana-clone`.

## Sync to the shared Confluence table

Set credentials, then run the sync script. It joins pre/post lines, skips rows
already synced, and appends new rows to the page (creating the table on first
run). Safe to run repeatedly and by multiple teammates against the same page.

```bash
export CONFLUENCE_EMAIL="you@pearson.com"
export CONFLUENCE_API_TOKEN="..."   # https://id.atlassian.com/manage-profile/security/api-tokens
# Defaults target the AIC4E "Cookie's MCPs invocation log" page:
# export CONFLUENCE_BASE_URL="https://pearson.atlassian.net/wiki"
# export CONFLUENCE_PAGE_ID="1221918747"

python3 /path/to/mcp-audit-plugin/scripts/sync-to-confluence.py --dry-run   # preview
python3 /path/to/mcp-audit-plugin/scripts/sync-to-confluence.py             # push
```

To automate it, add a cron entry or a Claude Code scheduled task that runs the
sync command periodically.

## Design guarantees

- **Observe-only.** Hooks never block a tool call and always exit 0, even on
  internal error.
- **Scoped.** Only MCP tools reach the hook (matcher `^mcp__`), and only your
  configured servers are logged. Calls from other servers produce nothing.
- **User-scoped.** Config and logs live under `~/.claude/mcp-audit`, so auditing
  applies across all your projects.
- **Fast & dependency-light.** Pure `python3` standard library; no pip installs.

## Not covered yet: "should have been called but wasn't"

A hook can't detect an *absent* call — there's no event for it. `scripts/
session-end-reviewer.py` is a documented stub for a future `SessionEnd`
reviewer that diffs session intent (transcript) against the call log. See the
file header for the intended design and how to enable it.

## Layout

```
mcp-audit-plugin/
├── .claude-plugin/plugin.json     # plugin manifest
├── hooks/
│   ├── hooks.json                 # registers Pre/PostToolUse on ^mcp__
│   └── audit.py                   # the hook (handles both events)
├── scripts/
│   ├── init-config.sh             # choose servers -> config.json
│   ├── sync-to-confluence.py      # push rows to the shared table
│   └── session-end-reviewer.py    # stub for missing-call detection
├── config.example.json
└── README.md
```
