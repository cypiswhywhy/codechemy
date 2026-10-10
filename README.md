# codechemy

Sharper [Claude Code](https://claude.com/claude-code) sessions. The `engineering-practices`
plugin holds every session to the same engineering contract, and ships skills for the work
around the code: framing a change, reviewing your own diff, shipping a PR, auditing a repo or
your own setup. Also here: templates for automated GitHub Copilot code review.

## Install

```bash
claude plugin marketplace add cypiswhywhy/codechemy && claude plugin install engineering-practices@codechemy
```

Then restart Claude Code. Updating, uninstalling, prerequisites and per-repository setup:
[docs/usage/install.md](docs/usage/install.md).

## Usage

Nothing to run: every new session starts with the contract, and the Stop hook checks the
change before the agent hands back. Skills run on demand, for example:

```text
/push
```

Guides: [docs/usage/](docs/usage/README.md).

## Reference

Practices, hooks, skills, settings and `make` targets: [docs/reference/](docs/reference/README.md).

## Internals

How the plugin is built and why, for engineers: [docs/internals/](docs/internals/README.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
