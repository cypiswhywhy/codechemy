## Maintenance toolbox
<!-- maintenance-toolbox: recorded 2026-09-10 by /maintenance-toolbox -->
Run before deleting anything, and again before handing back:
- Dead code: `uvx vulture . --min-confidence 80`
- Unused imports/vars: `uvx ruff check --select F401,F841,ARG .`
- Tests: `pytest`
Not available here: unused dependencies — no Python manifest; coverage — not configured.
