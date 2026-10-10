# Make targets

Run from the repository root.

| Target | Does |
|---|---|
| `make check` | lists the commands each skill and the plugin need (`git`, `gh`, `python3`, `openspec`, `claude`); exits non-zero if any is missing |
| `make install-plugin` | runs `check` without stopping on it, points the `codechemy` marketplace at this clone, then updates the plugin or installs it |
| `make uninstall-plugin` | uninstalls the plugin and removes the marketplace; already gone is not an error |
| `make migrate-skills` | removes skill copies an install before 2.0.0 put in `~/.claude/skills` |

`install-plugin` only refreshes an existing install when `version` in the plugin's
`plugin.json` has gone up. `claude` is the one hard requirement: the plugin targets stop
without it.
