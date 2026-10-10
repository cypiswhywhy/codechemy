# Install

```bash
claude plugin marketplace add cypiswhywhy/codechemy && claude plugin install engineering-practices@codechemy
```

Or paste this into any Claude Code session:

> Add the Claude Code marketplace `cypiswhywhy/codechemy` and install the
> `engineering-practices` plugin from it, then show me `claude plugin details
> engineering-practices`.

Restart Claude Code afterwards so the hooks and skills load. Runs on macOS or Linux.

## Prerequisites

A missing command disables only what calls it.

| Command | Needed by | Get it |
|---|---|---|
| `python3` 3.9+ | the hooks, `/codebase-maintenance`, `/claude-customizations` | https://www.python.org/downloads |
| `git` | the hooks, `/push`, `/codebase-maintenance`, both increment skills | https://git-scm.com/downloads |
| `gh` | `/push`, `/codebase-maintenance`, both increment skills | https://cli.github.com |
| `openspec` | `/apply-increment`, `/apply-all-increments` | `npm install -g @fission-ai/openspec` |

## Update and uninstall

```bash
claude plugin marketplace update codechemy   # pull new versions
claude plugin update engineering-practices
claude plugin uninstall engineering-practices
```

Updates are version-driven: a change reaches your install only once the plugin's `version`
goes up. `/plugin` does the same interactively.

## Enable it for a whole repository

Commit this to the project's `.claude/settings.json`, and every clone gets the plugin with no
command at all:

```json
{
  "extraKnownMarketplaces": {
    "codechemy": {"source": {"source": "github", "repo": "cypiswhywhy/codechemy"}}
  },
  "enabledPlugins": {"engineering-practices@codechemy": true}
}
```

## Upgrading from a version before 2.0.0

Back then the skills were copied into `~/.claude/skills`. Those copies shadow the plugin's, so
remove them once, from a clone of this repository:

```bash
make migrate-skills
```
