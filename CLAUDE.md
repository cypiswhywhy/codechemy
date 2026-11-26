## Maintenance toolbox
<!-- maintenance-toolbox: recorded 2026-09-10 by /maintenance-toolbox -->
Run before deleting anything, and again before handing back:
- Dead code: `uvx vulture . --min-confidence 80`
- Unused imports/vars: `uvx ruff check --select F401,F841,ARG .`
- Tests: `pytest`
Not available here: unused dependencies — no Python manifest; coverage — not configured.

## Project workflow
<!-- project-workflow: recorded 2026-11-26 by /kick-off -->
- Review: local
- Plan approval: ask - before editing code, show a short plan (what changes, in which files,
  which tests prove it) and wait for the user's yes. OpenSpec apply skills skip this: the
  change is the approved plan. A session that cannot ask (`claude -p`, CI, a subagent)
  states the plan and goes on.
- Jira: off
