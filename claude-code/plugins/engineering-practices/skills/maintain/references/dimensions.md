# Dimension checklists

One section per dimension. Each gives what to look for, what counts as evidence, and
what *not* to flag. The "do not flag" lists are the important half — they are where
audits lose the user's trust, by burying four real findings under twenty opinions.

Read the sections for the dimensions in scope before auditing.

## Contents

0. [RULES — agent instruction files](#rules--agent-instruction-files) (precondition)
1. [DEAD — dead code](#dead--dead-code)
2. [DUP — duplication](#dup--duplication)
3. [DEP — dependencies](#dep--dependencies)
4. [STYLE — style and consistency](#style--style-and-consistency)
5. [SEC — security](#sec--security)
6. [CORRECT — correctness](#correct--correctness)
7. [PRACTICE — design and best practice](#practice--design-and-best-practice)
8. [PERF — performance](#perf--performance)
9. [CLARITY — comprehensibility](#clarity--comprehensibility)
10. [TEST — coverage and test quality](#test--coverage-and-test-quality)
11. [DOC — documentation](#doc--documentation)

---

## RULES — agent instruction files

**Not a dimension** — a precondition, run in Phase 0 step 4 before any code is touched.
It changes how the project is worked on rather than the code, and it comes first
because Phase 0 grants `CLAUDE.md` / `AGENTS.md` authority over the whole run. A bad
rule there does not add noise; it silently disables entire dimensions, and the run
reports success having changed almost nothing.

**Risk class:** governance. Never applied without explicit approval.

### Look for

- **Blocks deletion** — "never remove existing code", "additions only". Turns `DEAD`
  into a no-op and guts `DUP`.
- **Blocks or discourages tests** — "do not write unit tests", "skip the suite", "tests
  are too slow to run". Removes the net every refactor depends on.
- **Mandates duplication** — "copy the class rather than extending it", "do not
  refactor shared code".
- **Waives review or verification** — "commit straight to main", "do not ask, just
  apply", "force-push freely". These remove the approval gate this skill runs on.
- **Waives security or correctness checks** — "disable the linter", "ignore scanner
  findings", "hardcode the token for local dev".
- **Self-contradictory**, or contradicts the linter config, so no behaviour satisfies
  both.
- **Stale** — names files, commands, directories or scripts that no longer exist.
  Cheap to verify and objectively wrong, so start here.

### Do not flag

This is where over-reach does real damage, and the failure mode is confident and
plausible. Many rules that pattern-match as harmful are load-bearing constraints
written by someone who got burned:

- "Never edit `migrations/`" — correct.
- "Do not remove anything under `api/v1/`" — probably a compatibility guarantee to
  callers outside this repo.
- "Do not touch `vendor/` or generated files" — exactly right.
- "Always keep the public API backwards compatible" — a deliberate product decision.
- "Do not run the integration suite locally" — it may need credentials or cost money.

A rule that looks wrong usually has a reason that simply is not written down. So the
move is **ask what the reason is, not assert the rule is wrong.** Quote the line, name
which dimension it blocks and what that costs, propose specific replacement wording,
and let the user decide.

If the user keeps a rule you flagged, that is the end of it: follow it, and say in the
final report which dimensions were limited as a result. A constrained run that respects
the project's rules is a good outcome; quietly overriding them is not.

### Applying

Findings get `RULES-nn` ids. Approved changes land in their own commit before any code
moves, so the governance change stays separable from the cleanup — and so a reviewer
can see the rule change that licensed everything after it.

---

## DEAD — dead code

**Risk class:** mechanical, *if* the evidence holds. Catastrophic if it does not.

### Look for

- Unreferenced functions, methods, types, constants, struct fields, class attributes.
- Exported symbols nothing imports (dead exports — the biggest win in most repos).
- Whole files and modules nobody imports.
- Commented-out code blocks. Version control already remembers them.
- Feature-flag debris: a flag permanently `true`, plus its dead branch and the flag
  itself.
- Unreachable branches — conditions that cannot be false, code after `return`,
  `except` clauses for exceptions the block cannot raise.
- Unused parameters, and unused imports the linter missed.
- Config keys, environment variables and CLI flags nothing reads.
- Test fixtures and helpers no test uses.
- Deprecated shims whose deprecation window has expired — check the date or version
  in the deprecation note.

### Evidence that counts

Two independent signals before deleting:

1. A tool says so — `deadcode ./...`, `vulture`, `ruff F401/F841`, `knip`, coverage
   showing zero executions across the whole suite.
2. A grep for the bare symbol name across *everything* — including non-source files:
   templates, YAML, JSON, SQL, Dockerfiles, CI config, shell scripts, docs.

Then rule out each dynamic-reachability path:

- **Reflection / dynamic dispatch** — `getattr`, `globals()`, `importlib`,
  `reflect.ValueOf`, `eval`, service locators, DI containers.
- **Registries** — decorators or `init()` functions that register by name; plugin
  discovery; entry points in `pyproject.toml` / `setup.py`.
- **Build tags and conditional compilation** — Go `//go:build`, platform-specific
  files. A symbol used only under `//go:build windows` is not dead.
- **External callers** — if the repo is a library, an exported symbol with no internal
  caller is its *product*, not dead code. Check whether it is published, and whether
  it is re-exported from the package root.
- **Operational entry points** — anything named in CI config, a Dockerfile `CMD`, a
  cron entry, a Makefile target, a systemd unit, a Helm chart.
- **Serialisation** — a struct field with no code reference may still be part of a
  wire format or a database row. Check the JSON/DB tags and any stored data.

If any of these cannot be ruled out, it becomes a question for the user, not a
deletion. Say what you found and what you could not rule out.

### Do not flag

- Interface methods that are unused but required to satisfy the interface.
- Test helpers used by only one test — that is fine.
- Exported API of a library, per above.
- `TODO` comments — those are `DOC` or a backlog item, not dead code.

---

## DUP — duplication

**Risk class:** behaviour-preserving, if extraction is genuinely mechanical.

### Look for

- Identical or near-identical blocks (a clone detector finds these; ~6+ lines is a
  useful floor).
- The same logic expressed differently in several places — three hand-rolled retry
  loops, four date-parsing helpers, two validators for the same field. A clone
  detector misses these; reading the module surface finds them.
- Repeated literals and magic values that should be one constant.
- Parallel `switch`/`if-elif` chains over the same enum in different files — when
  adding a case means editing three places, that is duplication of *structure*.
- Copy-pasted test setup that a fixture or table-driven test would collapse.
- The same bug fixed in one copy and not the others. Divergence between clones is the
  strongest argument for extraction, and worth calling out explicitly.

### Evidence that counts

Clone-detector output plus a read of each site to confirm the duplication is *real*.
Two blocks can be textually identical and semantically unrelated — an extraction that
couples them is a mistake dressed as a cleanup.

Before proposing extraction, ask: do these sites need to change *together*? If yes,
extract. If they are the same today by coincidence and would evolve apart, leave them
alone and say why.

### Do not flag

- Similar-looking tests. Repetitive, explicit tests are often clearer than a clever
  parameterised one; and a test's job is to be obvious when it fails.
- Boilerplate the language requires (Go error checks, `__init__` assignments).
- Generated code.
- Two- or three-line similarities. Extracting those costs a name and an indirection to
  save nothing.

---

## DEP — dependencies

**Risk class:** removals are mechanical; patch/minor bumps are low; majors are
behaviour-changing.

### Look for

- Declared but unimported.
- Imported but undeclared (works locally by transitive luck, breaks in a clean build).
- Known vulnerabilities — `govulncheck`, `pip-audit`.
- End-of-life or unmaintained: last release, open-issue trend, archived flag,
  deprecation notice.
- A heavyweight dependency used for one trivial function that the standard library
  now covers.
- Two dependencies doing the same job (two HTTP clients, two date libraries).
- Test/dev dependencies declared as runtime dependencies.
- Version drift between manifest, lockfile and what CI actually installs.
- Unpinned or wildly loose constraints in a service, where reproducible builds matter.

### Sequencing

Order matters, and each gets its own commit:

1. Remove unused (mechanical, no behaviour change).
2. Patch and minor bumps together, verified by the suite.
3. Each major bump on its own, in its own PR, with the changelog read and migration
   notes summarised. Never bundle a major with anything else — when it breaks
   something you want the bisect to land on one line.

Run `DEP` after `DEAD`: deleting code often removes a dependency's last user, and
that removal is free.

### Do not flag

- A pinned old version with a comment explaining the pin. Read the comment first.
- Transitive dependencies — address the direct parent, not the leaf.
- "Newer version exists" with no security, bug or capability reason. Churn is not
  maintenance.

---

## STYLE — style and consistency

**Risk class:** mechanical.

The goal is internal consistency, not conformance to your taste. Precedence:

1. What the project states — `CLAUDE.md`, `CONTRIBUTING.md`, linter config.
2. What the project consistently does, even where unstated.
3. Only where the codebase contradicts itself: pick the variant that appears most
   often, and say that is why.

### Look for

- Formatter and linter violations, once the *project's own* config is what you run.
- Naming inconsistency for the same concept — `userId` / `user_id` / `uid` in one
  codebase; `get_*` vs `fetch_*` vs `load_*` for the same kind of operation.
- Inconsistent error handling idiom — wrapped in some places, bare in others.
- Import ordering and grouping, where the project has a convention.
- Inconsistent structure: some packages layered, others flat, with no reason.
- Missing or inconsistent type annotations in a codebase that otherwise has them.
- Mixed line endings, stray tabs, trailing whitespace, missing final newline.

### Do not flag

- Anything the project's linter config deliberately disables. Someone chose that.
- Style in generated or vendored files.
- Your preference where the codebase is already consistent in the other direction.
  This is the main failure mode of this dimension.

### Applying

Auto-fixable violations in one commit, per formatter/linter, touching only files in
scope. Do not reformat the whole repo unless the user explicitly opts in — see the
`git blame` guardrail in SKILL.md.

---

## SEC — security

**Risk class:** the fix usually changes behaviour, and that is intended.

### Look for

- **Injection** — SQL built by concatenation or f-string; shell commands via
  `shell=True` or `os.system` with interpolated input; template injection; path
  traversal from user-supplied paths.
- **Secrets in the repo** — keys, tokens, passwords, connection strings, private keys,
  in source, config, fixtures, or committed `.env` files. Check git history too: a
  secret deleted in a later commit is still a leaked secret and needs rotation, not
  just deletion.
- **Weak crypto** — MD5/SHA1 for anything security-relevant, ECB mode, hardcoded IVs,
  `random` instead of `secrets`/`crypto/rand` for tokens, custom crypto.
- **AuthN/AuthZ** — endpoints missing an auth check; authorisation checked in the UI
  but not the API; IDOR (an object fetched by user-supplied ID with no ownership
  check); tokens with no expiry; missing MFA on privileged paths.
- **Unsafe deserialisation** — `pickle`, `yaml.load` without `SafeLoader`, unbounded
  `eval`.
- **Input validation** — unvalidated at the trust boundary; unbounded size on
  uploads, request bodies, or pagination.
- **Output encoding** — unescaped user data in HTML, or in log lines (log injection).
- **Transport and config** — TLS verification disabled, permissive CORS (`*` with
  credentials), debug mode reachable in production, default credentials, overly broad
  IAM or filesystem permissions.
- **Logging leaks** — secrets, tokens, full request bodies, or PII in logs. Cross-check
  with `DOC`/`LOG` conventions in the project.
- **Dependency vulnerabilities** — overlaps `DEP`; report under whichever the user is
  more likely to act on, not both.

### Evidence that counts

For each finding, state the *reachable path* from untrusted input to the sink. A
parameterless internal helper that concatenates SQL from a hardcoded constant is not an
injection. Naming the input source, the path and the sink is what separates a real
finding from a scanner echo — and it is what lets the user judge severity.

### Do not flag

- Test fixtures with obviously fake credentials (`password123`, `test-key`), unless
  the same value appears in non-test code.
- Theoretical issues with no reachable path from untrusted input.
- Findings a scanner produced that you have not confirmed by reading the code.

If a finding is a live exploitable issue in deployed code, say so first and separately
rather than burying it in the plan. Severity ordering matters more here than anywhere
else.

---

## CORRECT — correctness

**Risk class:** behaviour-changing by definition. Note it in the commit body.

### Look for

- **Swallowed errors** — bare `except: pass`, `_ = err`, a caught exception that logs
  and continues into an invalid state.
- **Unhandled edge cases** — empty collection, single element, zero, negative,
  off-by-one at boundaries, `None`/`nil` where a value is assumed.
- **Resource leaks** — unclosed files, connections, cursors, response bodies; missing
  `defer`/`with`/context manager.
- **Concurrency** — shared mutable state without synchronisation, races on
  check-then-act, deadlock-prone lock ordering, goroutines with no way to exit,
  unbuffered channel writes with no reader, missing context cancellation.
- **Numeric** — integer division where float was meant, float equality comparison,
  money in floats, overflow, silent truncation.
- **Time and locale** — naive datetimes mixed with aware ones, local time where UTC
  was meant, DST assumptions, string comparison of dates.
- **Contract mismatches** — a function whose docstring, name, or type signature
  disagrees with what it does. Whichever is wrong, that is a finding.
- **Validation that does not** — a check whose result is computed and discarded.
- **Silent partial failure** — a batch operation that reports success when some items
  failed.

### Evidence that counts

The concrete input or interleaving that produces the wrong result. "This could
theoretically race" is weak; "two concurrent calls to `Increment` both read 5 and both
write 6" is a finding. Where practical, write the failing test first — it proves the bug
and becomes the regression guard.

### Do not flag

- Defensive checks for conditions the type system already rules out, unless the
  codebase is inconsistent about it.
- Bugs in dead code — delete it under `DEAD` instead.

---

## PRACTICE — design and best practice

**Risk class:** behaviour-preserving in intent, highest-risk in practice. Needs the
test net.

### Look for

- **Single responsibility, honestly applied** — a module or class with several
  unrelated reasons to change. The tell is the commit history: if changes to feature A
  and feature B always touch the same file for unrelated reasons, it is doing two jobs.
- **Coupling** — reaching through objects (`a.b.c.d`), business logic depending on a
  concrete database or HTTP client, circular imports, a shared "utils" module everything
  depends on.
- **Leaky abstractions** — an interface whose callers must know the implementation; a
  repository returning ORM objects; errors from the storage layer surfacing as SQL
  errors in the API layer.
- **Missing seams** — logic that cannot be tested without a real database or network,
  where a narrow interface would fix it. Untestable code is a design finding, not just
  a `TEST` finding.
- **Primitive obsession where it hurts** — passing three loose strings that must stay
  consistent, when one type would make the invalid combination unrepresentable.
- **Inconsistent error strategy** — exceptions in one layer, error returns in another,
  with no translation point.
- **Global mutable state** — module-level state that makes tests order-dependent.
- **God functions** — long functions doing several sequential jobs with no natural
  seam. Length alone is not the problem; *number of reasons to change* is.

### The test every PRACTICE finding must pass

Name the concrete thing the change makes possible: a change that becomes local instead
of scattered, a bug class that becomes unrepresentable, a test that becomes possible to
write. If you cannot name it, the finding is pattern-application for its own sake — drop
it. Interfaces with one implementation, factories that construct one type, and a
cohesive module split into six files by shape rather than by responsibility all make
the code worse while looking like architecture.

Prefer the smallest structural change that gets the benefit. Extracting one interface at
one seam is usually worth it; a layered rewrite usually is not, and belongs as a
proposal to the user rather than a maintenance commit.

### Do not flag

- Working code that simply is not how you would have written it.
- Missing abstraction for a variation point that does not vary yet.
- Anything the project's own stated architecture chose deliberately.

---

## PERF — performance

**Risk class:** behaviour-preserving if done right; readability-damaging if done
carelessly.

### Look for

- **Algorithmic complexity in a real hot path** — nested loops over the same data,
  linear scans inside loops, repeated sorting, list membership tests where a set
  belongs.
- **N+1 queries and requests** — a query inside a loop over query results. Usually the
  single largest real win in an application codebase.
- **Missing indexes** for a query pattern the code clearly relies on.
- **Repeated work** — recomputing an invariant inside a loop, re-parsing config per
  request, no caching on an expensive pure function.
- **Unnecessary materialisation** — loading a full table to count it, building a list
  where a generator or iterator would do, reading a whole file to process it line by
  line.
- **Allocation in hot loops**, string concatenation in a loop, unnecessary copies.
- **Blocking I/O on a request path** where async or a background job is available.
- **Missing pagination or limits** on anything that grows with data volume.

### The measurement rule

State how you know it matters. In descending order of strength: a profile from
production or a realistic load; a benchmark you wrote and ran; a complexity argument
plus the actual data volume; a complexity argument alone.

The last of those is a *question*, not a finding — present it as "this is O(n²) over
`enrollments`; how large does that get?" rather than proposing a fix.

Where you do optimise, commit the benchmark alongside. The benchmark outlives the
optimisation and stops the next person undoing it, and it is often the more valuable
half of the change.

### Do not flag

- Micro-optimisations in cold paths — startup, CLI parsing, one-off scripts, tests.
- Anything that trades real clarity for unmeasured speed.
- Compiler- or interpreter-level tricks that a future version will do better anyway.

---

## CLARITY — comprehensibility

**Risk class:** mechanical (renames, extraction) to behaviour-preserving.

This is the "purity and transparency" dimension: could a competent newcomer read this
and be right about what it does?

### Look for

- **Names that mislead or say nothing** — `data`, `tmp`, `helper`, `process()`,
  `manager`; a name that describes the implementation rather than the intent; a name
  that is now wrong because the code changed under it. Misleading names are worse than
  vague ones.
- **Hidden side effects** — a function named as a query that mutates, writes, or calls
  the network. A `get_user` that lazily creates one is a clarity bug.
- **Deep nesting** — three or more levels of conditionals that guard clauses or early
  returns would flatten.
- **Boolean parameters at the call site** — `render(doc, true, false)` tells the reader
  nothing.
- **Implicit coupling** — order-dependent calls with nothing expressing the dependency;
  state set in one place and assumed in another.
- **Comments that explain *what*** where the code should say it, and the reverse:
  non-obvious code with no comment explaining *why*. A comment recording a
  non-obvious reason, a workaround, or a constraint is the most valuable line in the
  file — never delete one of those as "noise".
- **Stale comments** contradicting the code. Fix or delete; a wrong comment is worse
  than none.
- **Long-winded inline comments.** A comment between statements should be one line,
  occasionally two. A paragraph wedged mid-function costs real readability: it pushes
  the code apart so less of it fits on screen, and it goes stale faster than the line
  it describes. Compress it to the one clause that carries the information — the reason
  a reader could not have guessed — and move any remaining explanation to the
  function's docstring, the commit message, or an ADR, where a reader goes looking for
  it. Compressing five lines to one is a clarity win, not a loss, provided the reason
  survives. Deleting the reason is not.
- **Magic values** with no name.
- **Long parameter lists** where several parameters always travel together.
- **Clever code** — a dense comprehension, a bit trick, an over-general abstraction
  where the plain version reads better.

### Do not flag

- Domain terminology that looks odd but is what the business calls it. Match the
  domain, not general English.
- Short names with conventional meaning in tight scope (`i`, `err`, `ctx`, `db`).
- Long functions that are genuinely one linear procedure and read fine top to bottom.

Renames are cheap and high-value, but they touch many lines. Group them into one
clearly-labelled commit so the reviewer can skim rather than read.

---

## TEST — coverage and test quality

**Risk class:** additive. The safest dimension, and the one that makes the others safe.

### Coverage gaps — look for

- Untested modules, ranked by *risk*, not by size: money, auth, permissions, data
  migration, external integrations, anything with intricate branching.
- Uncovered error paths and exception handlers. Usually the largest real gap, and
  where bugs actually live.
- Uncovered boundaries: empty, one, many, max, zero, negative, null.
- Bug fixes in the git history with no accompanying regression test.
- Missing integration coverage where units are tested individually but their
  interaction is not.
- Code the audit found hard to reason about — that is where a test is worth most.

### Test quality — look for

- **Tests with no assertion**, or that only assert "did not raise". They lift coverage
  and catch nothing, which is worse than no test because it looks like safety.
- **Tautological tests** that mock the thing under test, or assert the mock was called
  rather than that anything happened.
- **Over-mocking** — a test so tied to the implementation that any refactor breaks it.
  These actively obstruct the rest of this skill's work.
- **Flaky tests** — dependent on real time, sleeps, network, ordering, or shared
  mutable state.
- **Unclear failure** — a test whose failure message does not say what broke. When it
  fires at 2am, that message is the whole product.
- **Tests asserting implementation** rather than behaviour — private call sequences,
  log strings, internal state.
- **Missing negative cases** — only the happy path.
- **Names that do not say what is being tested** — `test_1`, `test_it_works`.

### Never make a red test green by editing the test

This is the one rule in this dimension that can actively cause harm, so it is worth
stating separately. A failing test is a claim that the code is broken, and the default
assumption is that the claim is true. Editing the assertion, loosening a comparison, or
deleting the case makes the suite green while leaving the defect in place — and now
nothing is warning anyone. That is strictly worse than the red suite you started with.

Order of investigation:

1. Reproduce and read the failure. What behaviour is asserted, what happened instead?
2. Work out the *intended* behaviour from the surrounding code, docs, types and git
   history — deliberately not from "what would make this pass".
3. If the code is wrong, fix the code and leave the test alone. It just did its job and
   is now the regression guard.
4. Only once the subject is demonstrably correct may the test be the problem: a stale
   expectation after a deliberate requirement change, a real flake (time, ordering,
   network, shared state), or an assertion that never matched the spec. Name which,
   and say why the code is right, before editing it.

`git log -S` on the assertion, or bisecting to the commit where it went red, usually
settles it faster than reasoning about the code. If it stays ambiguous, ask the user —
that is a question, not a coin flip.

### The rule on coverage numbers

Coverage measures execution, not verification. Chase *behaviour* — branches, error
paths, boundaries — and let the number follow. If the user names a target, get there
with meaningful tests and tell them honestly when the remaining percent would mean
testing generated code, trivial accessors, or unreachable defensive branches. Reporting
"85% with the error paths now covered" is a better outcome than "100%" bought with
assertion-free tests, and worth saying out loud.

### Do not flag

- Missing tests for generated code or trivial accessors.
- Absence of a test type the project deliberately does not use.

---

## DOC — documentation

**Risk class:** mechanical. Runs last, because it describes the end state.

Two goals in order: **accurate first, short second.** A wrong document is worse than a
missing one, because someone will trust it.

### Look for

- **Contradicted by the code** — documented flags, endpoints, env vars, config keys,
  return values or defaults that no longer match. Highest priority; these actively
  mislead.
- **Setup instructions that do not work** — wrong commands, missing prerequisites,
  removed scripts. Check them against the actual `Makefile` and CI config.
- **Docs for things this run deleted**, and missing docs for things it changed.
- **Undocumented public API** — exported functions, endpoints, config, in a codebase
  that documents the rest.
- **Missing "why"** — an architecture decision with no record. Where the project keeps
  ADRs, a decision made during this run belongs in one.
- **Bloat that carries no information** — restating the obvious, duplicated across
  README and docs pages, tutorials for removed features, changelog entries better left
  to git.
- **Broken links and stale references.**
- **Prose describing a structure a diagram would show better** — a request flow, a
  state machine, a layered architecture. One Mermaid diagram often replaces three
  paragraphs and is easier to keep true.

### Do not flag

- Deliberately verbose user-facing tutorials. Brevity serves reference docs; teaching
  material has different rules.
- Missing docs for internal helpers.
- Historical changelog and ADR entries. Those are records, not stale docs — they are
  *supposed* to describe the past.

If the project already has a documentation convention or a docs skill, follow it rather
than imposing a new structure.
