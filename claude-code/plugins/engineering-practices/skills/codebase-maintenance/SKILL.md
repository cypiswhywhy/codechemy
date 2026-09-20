---
name: codebase-maintenance
description: End-to-end maintenance of an existing codebase, from audit to merge-ready pull request, in a single invocation. Audits eleven quality dimensions — dead code, duplication, dependencies, style consistency, security, correctness, design/SOLID, performance, clarity, test coverage and test quality, and documentation — then applies the findings as small verified commits, one per dimension, pushes, opens the PR, drives the automated review to green, and files whatever it did not do as issues. The user only reviews and merges. Starts by vetting the project's own CLAUDE.md / AGENTS.md for instructions that contradict good practice (blocking deletion, discouraging tests, mandating duplication), since such a rule silently disables whole dimensions. Interrupts at most once, for genuine judgment calls, and only after the safe work is already delivered; when the work exceeds one session it stops at a phase boundary and hands over a copy-pasteable prompt to continue in a fresh one. Use this whenever the user wants to clean up, slim down, tidy, harden, modernize, refactor, audit, or improve the quality of an existing repository; whenever they mention technical debt, code smells, dead code, duplication, "get this codebase in shape", or ask for a codebase review with the fixes actually applied. Also use it for narrower requests targeting one dimension — "find unused code", "why is our test coverage so bad", "make the style consistent", "check this repo for security issues", "our dependencies are ancient", "review my CLAUDE.md for bad instructions". Do not use it to write new features, or to review an uncommitted diff or a PR (use a code-review skill for that).
---

# Codebase maintenance

Take an existing repository from "it works" to "it works, it is smaller, and the next
person can understand it" — without changing what it does.

**One invocation carries the work to merge-ready pull requests.** The user's only
remaining jobs are reviewing and merging — not orchestrating. So a single run audits,
applies, verifies, commits, pushes, opens the PR and drives the automated review to
green, then files what it did not do as issues. It interrupts at most once, for genuine
judgment calls, and it does that *after* the safe work is already delivered. When the
work is too large for one session it stops at a phase boundary and hands over a
copy-pasteable prompt for a fresh one, rather than degrading as context runs out.

Three properties make this succeed or fail:

**The diff has to be reviewable.** Ten dimensions applied at once produces a
three-thousand-line diff that mixes deletions, formatting, refactors and behaviour
changes. Nobody can review that, so it gets rubber-stamped or thrown away whole — and
when something breaks, there is no way to tell which change did it. So: audit
everything at once, but apply in small batches, one dimension per commit, each verified
green before the next begins.

**Nothing may quietly change behaviour.** The user is asking for maintenance, not a
rewrite. A "cleanup" that alters an edge case is worse than no cleanup at all, because
it spends trust. Every batch is bracketed by a passing test run, and anything that
genuinely does change behaviour gets called out and approved rather than slipped in.

## The eleven dimensions

| ID | Dimension | What it targets |
|----|-----------|-----------------|
| `DEAD` | Dead code | Unreachable code, unused exports, commented-out blocks, flag debris |
| `DUP` | Duplication | Copy-paste and near-duplicate logic |
| `DEP` | Dependencies | Unused, outdated, vulnerable, end-of-life |
| `STYLE` | Style & consistency | Divergence from the project's own idiom |
| `SEC` | Security | Injection, secrets, authz gaps, unsafe defaults |
| `CORRECT` | Correctness | Real bugs, unhandled edges, swallowed errors |
| `PRACTICE` | Design | Coupling, cohesion, SOLID, leaky abstractions |
| `PERF` | Performance | Measured hot paths only |
| `CLARITY` | Comprehensibility | Naming, complexity, hidden side effects |
| `TEST` | Tests | Coverage gaps and test quality |
| `DOC` | Documentation | Accuracy, then brevity |

`references/dimensions.md` holds the working checklist for each one — what counts as
evidence, and just as importantly what *not* to flag. Read the entries for the
dimensions in scope before auditing; skimming produces generic findings that waste the
user's review time.

## Phase 0 — Orient

Do not skip this. Most bad maintenance runs come from starting to edit before knowing
what green looks like.

**1. Require a clean tree.** `git status --porcelain`. If there is any output, stop and
ask the user to commit or stash first. A maintenance run needs a known-good starting
point to bracket and, if necessary, revert to.

**2. Create a working branch.** `git switch -c chore/maintenance-<yyyy-mm-dd>`. Never
work on `main`.

**3. Read the project's own conventions.** Read, in this order: `CLAUDE.md` (or
`AGENTS.md`), `CONTRIBUTING.md`, `README.md`, then linter and formatter config
(`.golangci.yml`, `ruff.toml`, `pyproject.toml`, `.editorconfig`, `Makefile`).

This matters more than it looks. For `STYLE`, `PRACTICE` and `CLARITY` the target is
consistency with *this codebase's* idiom, not conversion to your own preferences. A
codebase that consistently does something you would not have chosen is in better shape
than one half-converted to your taste. When the project has a stated convention, it
wins; when it has an unstated but consistent habit, that habit wins; only where the
codebase actually contradicts itself do you get to pick, and then you pick the variant
that already appears most often.

**4. Vet the agent instructions before adopting them.** Step 3 hands `CLAUDE.md` /
`AGENTS.md` authority over the entire run, so read it once more with a different
question: does anything in here contradict the practice this skill is about to apply?

Do this before anything else touches code, because a bad rule does not merely add
noise — it silently disables whole dimensions. "Only additions are allowed, never
delete" turns `DEAD` into a no-op and guts `DUP`. "Do not write tests" removes the
safety net every refactor depends on. You would run the full audit, report success,
and have changed almost nothing, without ever noticing why.

Broadly: rules that block deletion, discourage tests, mandate duplication, waive review
or security checks, contradict the linter config, or are simply stale. The `RULES`
section of `references/dimensions.md` has the full checklist — read it before this step,
particularly the **do not flag** list, because over-reach here does real damage. Plenty
of rules that pattern-match as harmful are load-bearing ("never edit `migrations/`" is
correct), so ask what the reason is rather than asserting the rule is wrong.

Findings get `RULES-nn` ids. Nothing here is applied without explicit approval, and
approved changes land in their own commit before any code moves. If the user keeps a
rule you flagged, follow it and note in the final report which dimensions it limited.

**5. Establish the safety net.** Find and run the build, test and lint commands
(`Makefile` targets first, then the language default). Record whether each passes.

This is a gate, not a formality:

- **Tests pass** → the full workflow is available.
- **Tests fail** → stop and diagnose before touching anything else, and diagnose in
  the right order (below). You cannot verify a refactor against a suite that was
  already red.
- **No tests at all** → say so plainly and treat it as the headline finding. Restrict
  the run to changes that are safe without a net (dead code with positive evidence,
  formatting, docs, dependency tidying) and offer to write characterisation tests
  around any module the user wants refactored. Refactoring untested code is editing it
  and hoping.

### A failing test is a bug report until proven otherwise

When a test is red, the tempting move is to make it green. Resist it, because the
default explanation for a failing test is that **the code under test is broken**, and
editing the test is how you delete the bug report. The user asked for maintenance and
would get a suite that passes over a live defect — strictly worse than the red suite
they started with, because now nothing is warning them.

So work in this order:

1. **Read the failure.** What behaviour does the test assert, and what actually
   happened? Reproduce it directly if you can.
2. **Decide whether the assertion is right.** Judge the *intended* behaviour from the
   surrounding code, docs, types and git history — not from what makes the test pass.
3. **If the code is wrong, fix the code.** Leave the test exactly as it is: it just did
   its job, and it is now your regression guard.
4. **Only once the subject is demonstrably correct** consider the test itself at fault
   — a stale expectation after a deliberate requirement change, a genuine flake
   (time, ordering, network), or an assertion that never matched the spec. Say which of
   those it is, and why the code is right, before changing a line of it.

Loosening an assertion or deleting a case to get green is almost never the answer. If
you cannot tell whether the code or the test is wrong, that is a question for the user,
not a coin flip — and the git history usually settles it: find the commit where it went
red and read what it was trying to do.

**6. Snapshot the metrics.** This is what turns "the codebase is in better shape" from
an assertion into a measurement:

```bash
python3 <skill-dir>/scripts/metrics.py snapshot --out .maintenance/before.json
```

**7. Keep the workspace local.** The plan and snapshots live in `.maintenance/` and are
scaffolding, not deliverables — they should not end up in the diff. Exclude them
locally rather than editing the project's `.gitignore`:

```bash
mkdir -p .maintenance && echo '.maintenance/' >> .git/info/exclude
```

If `.maintenance/plan.md` is already there, an earlier run left a backlog and a set of
decisions worth honouring — Phase 2 says what to do with it. Mention it when agreeing
scope in step 8, since it may already answer what to work on.

**8. Agree the scope.** Two things to settle: which dimensions, and which paths.

If the invocation carried arguments, they *are* the scope — take them and move on
rather than asking a question the user has already answered. Paths narrow the tree
(`/codebase-maintenance internal/auth`); dimension IDs or their plain-English
equivalents narrow the audit (`--only DEAD,DUP`, or "just dead code and duplication").
A bare invocation means no scope was given, so propose the default and confirm it.

The default is all eleven dimensions over the whole repo minus vendored and generated
code — but let a narrow request stay narrow. Someone who asked "find our dead code"
wants `DEAD`, maybe `DUP`, and a report; running all eleven on them is not
thoroughness, it is not listening. Where a neighbouring dimension would clearly help,
offer it as a follow-up at the end instead of quietly widening the run.

## Phase 1 — Audit (read-only)

Nothing is edited in this phase. The output is findings.

The dimensions are independent read-only investigations, which makes them a good fit
for parallel subagents — one per dimension, each returning structured findings. That
also keeps eleven dimensions' worth of file reads out of a single context window, which
matters on a large repo. If subagents are unavailable, work through the dimensions
sequentially in the Phase 3 order; the result is the same, it just takes longer.

Give each auditor: the paths in scope, the conventions learned in Phase 0, the relevant
`references/dimensions.md` section, and the language reference (`references/go.md`,
`references/python.md`) so it uses real tooling rather than reading files by eye. Tool
output is evidence; unaided reading is a hypothesis.

Every finding needs these fields, because the user's triage decision depends on all of
them:

```
ID:        DEAD-03                      # <DIMENSION>-<n>
Location:  internal/auth/legacy.go:14-88
What:      ValidateLegacyToken and its two helpers are unreferenced.
Why:       Evidence — `deadcode ./...` reports it; grep finds no callers, no
           reflection, no build tags, not exported from the module root.
Risk:      mechanical | behaviour-preserving | behaviour-changing
Effort:    S | M | L
Value:     -74 LOC; removes the last caller of the deprecated jwt-go dependency.
Action:    Delete the function and its helpers; drop the dependency in DEP-02.
```

Two rules that keep the audit honest:

**Report evidence, not suspicion.** "This might be unused" is not a finding, it is a
task you have not finished. Either establish that it is unused, or flag it as a
question for the user. Findings that turn out to be wrong cost far more trust than
findings you never made.

**A finding you would not act on does not belong in the list.** Resist padding. Thirty
findings the user has to wade through to reach the four that matter is a worse audit
than five well-chosen ones. Fold trivia into a single "assorted lint" line item.

## Phase 2 — Triage

**First, look for a plan from an earlier run.** A partly-completed plan is the normal
outcome of a full-scope run, not a failure — the user defers items at triage, major
dependency bumps are one-per-PR by rule, a batch that failed verification gets
reverted and deferred, a kept `CLAUDE.md` rule blocks a dimension, or the session
simply ended. So on any repo this skill has touched before, expect a backlog.

If `.maintenance/plan.md` exists, read it before writing anything:

- **`rejected` items are decisions the user already made — do not re-propose them.**
  Re-raising a settled question is how a second pass turns into re-litigation, and it
  is the fastest way to make the run feel like it is not listening. The one exception
  is a rejection whose recorded reason has since become void — a rule that was later
  changed, a dependency since upgraded — which may be raised once, explicitly framed
  as "previously rejected because X, which no longer holds".
- **`deferred` and unapproved `proposed` items are pre-triaged backlog.** Carry them
  forward as candidates, but re-verify each against the current code first. A plan from
  three months ago describes a repo that no longer exists, and a finding that has since
  been fixed or deleted must not reappear as though it were fresh.
- **`done` items need no action.** If one regressed, this run's audit finds it again on
  its own evidence, which is the right way for it to resurface.

**A status with no reason still stands.** Older plans, and those written by hand, often
record a bare `rejected` or `deferred` with nothing beside it. Honour it anyway: the
user made that decision, and the reasoning being unwritten does not withdraw it. The
temptation is to treat an unexplained rejection as unreliable and re-raise it, which
gets the trade exactly backwards — re-proposing something the user already declined
costs them the same annoyance whether or not you can see why they declined it.

So carry a reasonless `rejected` forward as rejected, and list those items in the final
report as decided-but-unexplained rather than quietly acting on them either way. If one
genuinely blocks something this run needs to do, ask about that specific item and say
the reason is missing from the plan — a targeted question is fine, reopening the whole
set is not. Reasonless `deferred` items need no special handling: they were already
going to be re-verified against current code.

Then move the old file aside as `plan-run<N>.md` and write a clean one, rather than
editing a record of a different run.

Treat a prior plan as a hint set, never as truth: it tells you what was considered and
what the user decided, while the current audit is what establishes what is true now.
Where the two disagree, the audit wins — except on rejections, where the user does.

Write `.maintenance/plan.md`: findings grouped by dimension, in the Phase 3 apply
order, each with a status of `proposed` / `approved` / `rejected` / `deferred` / `done`.
Record the *reason* alongside every `rejected` and `deferred` status. A later run will
honour the status either way — see above — but only a recorded reason lets it act well
on one: notice that the reason has since become void and the item is worth raising
again, explain to the user why something is not being done, or file a `deferred`
finding as an issue someone can act on. A bare status is obeyed; a status with its
reason is understood, and only the second lets the next run do anything more than
comply.

### Sort every finding into apply-now or ask

One invocation is expected to carry the work through to merge-ready pull requests, so
do not open by asking permission for the whole plan. Sort each finding instead, and
apply what does not need a decision.

**Apply without asking:**

- **Mechanical** — dead code with positive evidence, formatter and lint autofix,
  dependency tidy and patch/minor bumps, docs. No behaviour change is possible.
- **Behaviour-preserving and test-covered** — extraction, renames, guard clauses, small
  refactors, where the suite exercises the code and stays green. The tests are what
  make this safe, which is why the safety net comes first.
- **Security fixes and real bugs** (`SEC`, `CORRECT`). These *do* change behaviour, and
  that is the point — leaving a known injection or a swallowed error in place to ask
  about it later is the worse outcome. Say so in the commit body.

**Stop and ask** when any of these is true, because the cost of being wrong is a whole
PR of wasted work and review rather than one line:

- It breaks a public API or any documented contract.
- It is a **dependency major**.
- One logical change exceeds roughly 15 files or 400 non-deletion lines. The question is
  whether the scope is right, not whether to split it: one shippable piece of value is
  landed whole, however large it is.
- It is a `PERF` claim with no measurement behind it — ask whether to benchmark first.
- It is a structural `PRACTICE` change and you cannot name the concrete thing it makes
  possible. That inability *is* the finding failing its own test.
- The evidence for a deletion has a dynamic-reachability hole you could not close.

Deletion-heavy diffs do not count toward the size trigger the way new code does: a
2,000-line removal is far easier to review than 200 lines of restructuring.

### Ask once, and ask late

Apply everything in the first group *before* raising anything. Then ask a single
consolidated question about what is left. Two reasons: the user sees real, verified
progress before being asked to decide anything, and the safe majority is delivered even
if they step away and never answer.

If nothing landed in the ask group, do not ask at all. Report what was applied and keep
going — an interruption with no decision in it is pure cost.

When there is something to ask, make it answerable in one line:

> Applied and pushed: DEAD (−610 LOC), DUP-01..04 (−180 LOC), the DEP tidy, STYLE,
> SEC-01 (SQL string-concatenation in `reports/query.py:88`), CORRECT-02 (swallowed
> error in the retry loop). Suite green, PR #214 open.
>
> Three left that need your call:
> - `PRACTICE-01` — storage layer has four responsibilities; splitting touches 19
>   files. Worth doing, but its own PR.
> - `DEP-05` — SQLAlchemy 1.4 → 2.0, breaking major. Own PR, needs the changelog read.
> - `PERF-02` — the N+1 in `list_enrollments` is real, but nothing shows it matters at
>   your volumes. Benchmark it first?
>
> Say which to take on, or "none" and they become issues.

Silence is not consent for the ask group. Anything unanswered becomes a deferred
finding and then an issue in Phase 5 — never something applied by default.

## Phase 3 — Apply, in this order

The order is load-bearing. Each step either makes the next one safer or makes it
smaller.

0. **`RULES`** — approved changes to `CLAUDE.md` / `AGENTS.md`, in their own commit
   before any code moves. It comes first because the rules govern everything after it.
1. **Safety net** — get the suite green *by fixing whatever is actually broken*, per
   the failing-test order in Phase 0; then add characterisation tests around anything
   about to be refactored. Everything below depends on this.
2. **`DEAD`** — deleting first shrinks the surface every later dimension has to work
   over, and stops you polishing code that should not exist.
3. **`DUP`** — after deletion, because de-duplicating code that was about to be deleted
   is wasted work, and some duplication disappears with its dead copy.
4. **`DEP`** — after deletion, since removing code often removes a dependency's last
   user. Unused removals and version bumps go in separate commits; a major bump goes in
   its own PR.
5. **`STYLE`** — mechanical, so it lands as its own commit. Formatting mixed into a
   logic change makes the logic change unreviewable, and this is the single most common
   way a good cleanup becomes unmergeable.
6. **`SEC`** — high value, usually local, and worth landing early in case the run stops.
7. **`CORRECT`** — real bugs. Note in the commit body that behaviour changed, because
   it did, and that is the point.
8. **`PRACTICE`** + **`CLARITY`** — the riskiest work, done once the net is in place
   and the codebase is already smaller.
9. **`PERF`** — measured only. See the rule below.
10. **`TEST`** — coverage gaps and test quality, now aimed at the code's final shape.
11. **`DOC`** — last, because documentation describes the end state. Written earlier it
    just gets rewritten.

### The verification loop, per batch

```
apply one dimension's approved findings
  → run build, tests, lint
  → green?  commit
  → red?    fix it, or revert this batch and mark the finding `deferred` with the reason
```

Never move to the next batch over a red suite, and never leave the tree broken between
batches. If a finding cannot be applied cleanly, reverting it and saying so is a good
outcome; leaving it half-applied is not.

Commit as conventional commits, scoped to the dimension, with the *why* in the body:

```
refactor(reports): extract shared filter builder

Three functions in reports/ built the same WHERE clause. Extracted to
_build_filter(). Behaviour preserved — covered by the existing
test_report_filters suite.

Findings: DUP-01, DUP-02, DUP-03
```

Update each finding's status in `.maintenance/plan.md` as you go, so an interrupted run
can be resumed rather than restarted.


## Phase 4 — Deliver to a merge-ready PR

The run is not finished when the commits exist. Carry it to a pull request the user can
review and merge, so the only things left for them are reviewing and merging.

**Default to one PR with one commit per dimension.** The commits are already the review
unit, and a single PR keeps them in dependency order with no cross-branch conflicts.
Resist splitting for its own sake: the dimensions interact — that is why the apply order
exists — so two PRs off `main` touching the same files will conflict with each other and
block each other's review.

**Split only for a specific reason**, and there are only a few good ones: a dependency
major, a breaking change, a self-contained subsystem, or a PR grown too large to review
(roughly 800+ non-deletion lines — deletion-heavy diffs stay reviewable much longer).

When splitting, PRs go out **sequentially in apply order, never in parallel**. If a
later PR depends on an earlier one, stack it on that branch rather than on `main`, and
say so in the body: a reviewer needs to know they are looking at a diff that assumes
something unmerged. Independent chunks may branch from `main`.

Then push, open the PR, and drive the automated review to green. If the `push` skill is
available, invoke it — it already handles push, PR creation, and the automated review
loop. Never merge; that stays the user's.

`references/delivery.md` has the PR body template, the splitting decision list, and the
issue and handoff templates.

## Phase 5 — Report, file the backlog, hand off

**Measure.** Snapshot again and compare:

```bash
python3 <skill-dir>/scripts/metrics.py snapshot --out .maintenance/after.json
python3 <skill-dir>/scripts/metrics.py compare .maintenance/before.json .maintenance/after.json
```

**Report** — measured before → after (quoting only what the script actually measured,
and naming what was unavailable rather than estimating it), the commits, the PR links,
anything that changed behaviour however small, and the deferred and rejected items with
their reasons. That last part is the most useful section, because it is the backlog: an
honest "SQLAlchemy 2.0 needs its own PR" beats a claim of completeness.

**File the backlog as issues.** Surviving `deferred` findings go to the issue tracker,
because `.maintenance/plan.md` is local and untracked — it does not survive a machine,
teammates cannot see it, and nothing will remind anyone it exists. Creating issues is
outward-facing, so list what you intend to file and ask once before creating any. Then
one issue per finding, carrying id, location, what, why, risk, effort, and the reason it
was deferred. Never file issues for `rejected` items — those are decided.

**Name the gates worth adding.** Findings are also a list of missing CI checks: `STYLE`
findings mean the formatter is not enforced, `SEC` means no scanner runs, `DEAD` means
no dead-code pass, `TEST` means no coverage floor. Say which would have prevented what
you just fixed. A backlog cleared without gating regrows, and this is the difference
between one cleanup and a codebase that stays clean.

### When the work will not fit in one session

A large repo across eleven dimensions can outlast a single session's context. That is
expected, not a failure — so end deliberately rather than degrading. Stop at a **phase
or dimension boundary**, never mid-batch, when remaining work is clearly large or
context is running short.

To hand off cleanly:

1. Leave nothing uncommitted or unpushed, and leave the suite green.
2. Update `.maintenance/plan.md` — every finding's status and reason, and what is next.
3. Write the continuation prompt to `.maintenance/handoff.md`.
4. Print it to the user in a fenced block, ready to paste into a fresh session, and say
   plainly that this is a normal pause with the work so far already delivered.

The prompt must stand alone — a new session shares no context, so it carries the branch,
the plan path, what is done, and what comes next. `references/delivery.md` holds the
template.

## Guardrails

These exist because each one is a specific way this kind of work goes wrong.

**Deleting needs positive evidence, not absence of evidence.** Static analysis does not
see reflection, dependency injection, `getattr`, plugin registries, template lookups,
build tags, entry points named in CI or Dockerfiles, or the public API of a library that
your callers are outside this repo. Before deleting: grep for the name as a string,
check for dynamic dispatch, check whether the module root exports it, and check whether
the repo is a library. If you cannot rule those out, ask — a wrong deletion is the most
expensive mistake available here.

**Do not reformat files you were not otherwise editing.** A repo-wide format commit
destroys `git blame` for everyone. If the codebase genuinely needs one, propose it as a
separate, clearly-labelled commit and let the user decide.

**Optimise only what you have measured.** Without a profile or benchmark you are
guessing, and the usual result is code that is harder to read and no faster. If a
`PERF` finding has no measurement, either measure it (add a benchmark, commit it — the
benchmark outlives the optimisation) or hand the user the finding with an honest "this
looks quadratic but I have not shown it matters at your scale". Algorithmic complexity
in a proven hot path is worth fixing; micro-optimisation is not.

**Coverage is a proxy, and it is easy to cheat.** Tests that execute code without
asserting anything raise the number and catch nothing. Aim at behaviour — branches,
error paths, boundaries — and let the number follow; 70% with sharp tests beats 100% of
the smoke-test kind. See the `TEST` section of `references/dimensions.md`.

**SOLID is a means.** Patterns earn their place by making a specific change easier or a
specific bug impossible. An interface with one implementation adds indirection and calls
it architecture. Name the concrete thing a `PRACTICE` finding makes possible; if you
cannot, the finding just failed its own test.

**Keep inline comments short.** A comment in the middle of a function should be one
line, occasionally two — long enough to name the non-obvious reason, and no longer. A
paragraph wedged between statements is worse than no comment: it pushes the code apart
so less of it fits on screen, it goes stale faster than the line it sits above, and it
usually explains *what* the code does, which the code already says.

The reasoning that does not fit in a line belongs where a reader looks for it: the
function's docstring, the commit message, an ADR, or `references/`. So prefer
`# gofmt -l exits 0 even when it lists files` over four lines building up to it. This
applies to comments this skill *writes*, and it is also what `CLARITY` prunes when it
finds them — see the comment guidance in `references/dimensions.md`.

**Leave generated and vendored code alone.** `vendor/`, `node_modules/`, `*.pb.go`,
`*_gen.go`, `*_pb2.py`, migrations, lockfiles. Fix the generator or the manifest, never
the artefact.

**Preserve the public API** unless the user has explicitly approved a breaking change.
Deprecate and keep a shim; do not silently rename.

**Shorter is not the goal — smaller *at equal clarity* is.** "Slim the repo" means
removing what does not carry weight, not compressing what does. If a change reduces
line count and makes the code harder to follow, it is a regression. Deleting a
duplicated block is a win; collapsing a readable loop into a dense one-liner is not.

## References

- `references/dimensions.md` — per-dimension checklist: what to look for, what evidence
  counts, what not to flag. Read the sections in scope before auditing.
- `references/delivery.md` — PR bodies, split decisions, issue filing, session handoff.
- `references/go.md` — Go tooling per dimension, with commands.
- `references/python.md` — Python tooling per dimension, with commands.
- `scripts/metrics.py` — stack detection and before/after measurement.

For a language not covered by a reference, follow the same shape: find the project's
existing tooling first (`Makefile`, CI config, pre-commit hooks — the team has usually
already chosen), and prefer a tool the project already runs over one you introduce.
