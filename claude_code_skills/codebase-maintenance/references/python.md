# Python tooling

**Check the project first.** `pyproject.toml`, `setup.cfg`, `tox.ini`, `noxfile.py`,
`.pre-commit-config.yaml`, `Makefile` and CI workflows record the tooling and rule set
the team already chose. Prefer their commands and their configuration — matching the
team's gate means your findings are ones they will act on, and your fixes pass their CI.

Probe availability, and note in the audit what was unavailable rather than silently
skipping it:

```bash
command -v ruff mypy pytest vulture pip-audit radon pylint 2>/dev/null
python3 -c 'import sys; print(sys.version)'
```

Work inside the project's environment (`.venv`, `poetry env info -p`, `uv`) so imports
resolve. Install tools with `uv tool run` / `pipx run` rather than adding them to the
project's dependencies.

## Baseline

```bash
python3 -m compileall -q .                  # syntax check across the tree
ruff check .
mypy .                                      # only meaningful if the project uses it
pytest -q 2>&1 | tail -30
```

Record which of these already fail. A pre-existing `mypy` failure count is a baseline,
not a finding to fix in this run unless the user asks.

## DEAD

```bash
vulture . --min-confidence 80               # start high; 60 for a second pass
ruff check --select F401,F811,F841,ARG,ERA .
#   F401 unused import   F811 redefinition   F841 unused local
#   ARG  unused argument ERA  commented-out code
pyflakes .
deadcode .                                  # if available
```

For unused *exports* across modules, `vulture` is weak. Cross-check by hand:

```bash
grep -rn "def my_function\|my_function(" --include='*.py' .
grep -rn "my_function" --include='*.yaml' --include='*.toml' --include='*.cfg' \
     --include='*.html' --include='*.j2' --include='*.sql' .
```

Python-specific false positives to rule out before deleting — dynamic reachability is
much more common here than in Go:

- **`getattr` / `globals()` / `importlib`** — `grep -rn 'getattr(\|globals()\|importlib\|__import__' .`
- **Entry points** — `[project.scripts]` / `[project.entry-points]` in
  `pyproject.toml`, `console_scripts` in `setup.py`. Named as strings, invisible to
  static analysis.
- **Decorator registration** — Flask/FastAPI routes, Celery tasks, Click commands,
  pytest fixtures, `@register`, signal receivers, Django `AppConfig.ready`.
- **Framework-convention names** — Django models/migrations/admin, DRF serializer
  methods, pydantic validators, `Meta` classes, `settings.py` values,
  `conftest.py` fixtures, unittest `setUp`/`tearDown`.
- **`__all__`** — a symbol listed there is public API even with no internal caller.
- **Serialisation and ORM** — a model field or dataclass attribute with no code
  reference may map to a live database column. Check migrations and stored data before
  touching it.
- **String-referenced paths** — Django `urls.py` view strings, `INSTALLED_APPS`,
  Celery `task_routes`, `LOGGING` config handler paths, Alembic script locations.

Whole-tree `vulture` output on a Django or FastAPI project is mostly false positives.
Filter by the above before reporting anything.

## DUP

```bash
pylint --disable=all --enable=duplicate-code --min-similarity-lines=6 <pkg>
ruff check --select PLR0911,PLR0912,PLR1714 .
python3 -m pyflakes .
```

`jscpd` (`npx jscpd --languages python .`) is a decent language-agnostic clone
detector if the environment allows it.

For repeated *literals*, `ruff --select PLR2004` (magic value comparison) is a good
proxy.

## DEP

```bash
pip-audit                                   # known vulns; --fix suggests versions
pip list --outdated
pipdeptree --warn silence                    # who pulls what
deptry .                                     # unused / missing / misplaced deps
pip check                                    # broken requirements
```

Manifest hygiene checks:

- Declared-but-unimported and imported-but-undeclared: `deptry` is the best single
  tool for both.
- Dev tools (`pytest`, `ruff`, `mypy`) listed as runtime dependencies.
- Drift between `pyproject.toml` / `requirements.txt` and the lockfile
  (`poetry.lock`, `uv.lock`, `requirements.lock`).
- Unpinned constraints in a *service* — reproducible builds need pins; a *library*
  should stay loose. Judge by which the repo is, and do not "fix" a library's ranges.
- EOL Python itself: check `requires-python` against the
  [supported versions](https://devguide.python.org/versions/). Running on an
  end-of-life interpreter is a `DEP` finding worth raising early.

For bumps: `pip install -U <pkg> && pytest`. One major per commit; read the changelog
and summarise the migration in the commit body.

## STYLE

```bash
ruff format --diff .                        # or black --diff . if the project uses it
ruff check .                                # project's own config
ruff check --fix .                          # auto-fixable subset
ruff check --select I .                     # import sorting (isort-equivalent)
mypy --strict <pkg>                         # only if the project is already typed
```

If the project has no `ruff`/`black` config, run defaults and propose adding one as a
finding rather than applying a strict rule set the team never agreed to.

Type-annotation consistency is a real `STYLE` finding in Python: a codebase that is 80%
annotated is harder to work in than one that is 0% or 100%, because you cannot trust
the absence of an annotation to mean anything.

## SEC

```bash
bandit -r . -ll                             # -ll = medium and above
ruff check --select S .                     # bandit rules, built into ruff
pip-audit
semgrep --config=auto .                     # if available
detect-secrets scan                         # or: gitleaks detect
```

Read every `bandit` hit before reporting; B101 (assert), B404/B603 (subprocess) and
B608 (SQL) all fire on safe code routinely. Confirm the untrusted input path.

High-value greps:

```bash
grep -rn 'shell=True\|os.system\|eval(\|exec(' --include='*.py' .
grep -rn 'pickle.load\|yaml.load(' --include='*.py' .      # yaml without SafeLoader
grep -rn 'verify=False' --include='*.py' .                 # TLS verification off
grep -rn 'f".*SELECT\|f".*INSERT\|% *(.*SELECT\|+ *"WHERE' --include='*.py' .
grep -rn 'import random' --include='*.py' .                # tokens need `secrets`
grep -rn 'DEBUG *= *True\|ALLOWED_HOSTS *= *\[.\*.\]' --include='*.py' .
```

Django and Flask specifics worth checking: `DEBUG` reachable in production,
`SECRET_KEY` hardcoded, `ALLOWED_HOSTS = ['*']`, CSRF exemptions
(`@csrf_exempt`), `.raw()` / `.extra()` queryset calls, permissive CORS with
credentials, and `send_file`/`open` on a user-supplied path.

## CORRECT

```bash
mypy .                                      # the strongest bug-finder available here
pyright .                                   # alternative, often catches different things
ruff check --select B,RET,SIM,TRY,ASYNC,DTZ,PLE .
#   B    bugbear — real bug patterns      RET   return-path issues
#   SIM  simplifiable logic               TRY   exception antipatterns
#   DTZ  naive/aware datetime mistakes    ASYNC async pitfalls
pytest -p no:randomly -q                    # check for order dependence
```

Highest-value rule selections for this dimension:

- `B` (flake8-bugbear) — mutable default arguments, `except` ordering,
  `zip()` without `strict=`, loop-variable binding in closures.
- `TRY` — `except: pass`, bare `except`, raising inside `except` without `from`.
- `DTZ` — naive/aware `datetime` mixing, the classic silent correctness bug.
- `ASYNC` — blocking calls inside `async def`, which look fine and destroy throughput.

Also worth a direct grep, since they are frequently configured off:

```bash
grep -rn 'except.*:\s*$' -A1 --include='*.py' . | grep -B1 'pass'   # swallowed
grep -rn 'def .*=\s*\[\]\|def .*=\s*{}' --include='*.py' .          # mutable defaults
grep -rn 'datetime.now()\|datetime.utcnow()' --include='*.py' .     # naive datetimes
```

## PRACTICE / CLARITY

```bash
radon cc . -a -nc                           # cyclomatic complexity, C-grade and worse
radon mi . -nc                              # maintainability index
ruff check --select C901,PLR0913,PLR0912,PLR0915,FBT,N,D .
#   C901    complex function        PLR0913 too many arguments
#   PLR0912 too many branches       PLR0915 too many statements
#   FBT     boolean trap args       N       naming conventions
#   D       docstring conventions
pylint <pkg> --disable=all --enable=R        # refactor suggestions
import-linter lint                          # layer/contract violations, if configured
```

`FBT` (boolean trap) maps directly to the `CLARITY` finding about boolean parameters at
call sites, and `pydeps <pkg> --show-cycles` finds the circular imports that make a
`PRACTICE` coupling finding concrete.

## PERF

```bash
python3 -m cProfile -s cumtime -m <module> 2>&1 | head -40
py-spy record -o profile.svg -- python3 <script>     # sampling, works on running procs
pytest --durations=20                                 # slowest tests, often revealing
python3 -m timeit -s 'setup' 'stmt'
memray run <script> && memray flamegraph <out>        # allocations
ruff check --select PERF,C4 .                         # loop and comprehension patterns
```

For N+1 queries — usually the largest real win in a Python service — turn on query
logging rather than reading code:

- Django: `django-debug-toolbar`, or `settings.LOGGING` on `django.db.backends`, or
  `assertNumQueries` in a test.
- SQLAlchemy: `echo=True` on the engine, or the `before_cursor_execute` event.

An `assertNumQueries`-style test committed alongside the fix is the ideal `PERF`
artefact: it is the measurement *and* the regression guard.

## TEST

```bash
pytest --cov=<pkg> --cov-report=term-missing --cov-report=html
pytest --cov=<pkg> --cov-report=term-missing | sort -t'%' -k1 -n   # worst first
pytest --cov=<pkg> --cov-branch                     # branch coverage: the honest number
pytest -p randomly -q                                # order dependence
pytest --lf -q                                       # last failures
```

Branch coverage is the number to quote. Line coverage hides exactly the uncovered
error paths this dimension cares most about.

Quality signals specific to Python:

```bash
grep -rLn 'assert' --include='test_*.py' .           # test files with no assertion
grep -rn 'assert True\|assert not None\|pass  #' --include='test_*.py' .
grep -rn 'mock.patch\|MagicMock' --include='test_*.py' . | wc -l   # over-mocking scale
grep -rn 'time.sleep' --include='test_*.py' .        # flakiness source
grep -rn 'def test_\(1\|2\|it_works\|foo\)' --include='test_*.py' .
```

A test module where `mock.patch` count approaches the test count is usually asserting
implementation rather than behaviour — those tests will break under every `PRACTICE`
and `DUP` change in this run, so flagging them early is worth it.

Prefer `pytest.mark.parametrize` over copy-pasted cases, and `pytest.raises(X, match=...)`
over a bare `pytest.raises(Exception)` that passes on the wrong error.
