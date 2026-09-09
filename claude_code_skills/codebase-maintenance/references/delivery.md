# Delivery: PRs, issues, and session handoff

Templates and decision rules for Phase 4 and Phase 5. The goal throughout is that the
user's only remaining actions are reviewing and merging.

## Contents

1. [Should this be one PR or several?](#should-this-be-one-pr-or-several)
2. [PR body template](#pr-body-template)
3. [Filing deferred findings as issues](#filing-deferred-findings-as-issues)
4. [Session handoff](#session-handoff)

---

## Should this be one PR or several?

**Start from one PR.** One commit per dimension already gives commit-by-commit review,
in dependency order, with no cross-branch conflicts. Splitting costs the reviewer
context and costs you merge conflicts, so it needs a reason.

Split when one of these is true:

| Trigger | Why it earns its own PR |
|---|---|
| Dependency major | Needs the changelog read and may break callers; must be bisectable alone |
| Breaking API change | Needs its own discussion and possibly a deprecation window |
| Self-contained subsystem | Different reviewer, no overlap with the rest of the diff |
| Too large to review | Roughly 800+ non-deletion lines changed |

Not reasons to split: "the dimensions are conceptually different" (commits already
express that), or tidiness. Ten small PRs cost more review attention in total than one
well-staged PR, and the user's attention is the scarce resource.

### Sizing

Judge by **non-deletion** lines. A 2,000-line deletion PR is quick to review — the
question is only "was any of this reachable", and the commit body answers it. Two
hundred lines of restructuring is far more work to check. So do not split a large
`DEAD` commit; do consider splitting a large `PRACTICE` one.

### Ordering when you do split

Sequential, in apply order, never in parallel. Overlapping files mean the second PR
must branch from the first, not from `main`:

```bash
# dependent: stack it
git switch -c chore/maintenance-practice chore/maintenance-base

# independent: branch from the default branch
git switch -c chore/maintenance-deps main
```

A stacked PR must say so at the top of its body — "Stacked on #214, review that
first" — because a reviewer needs to know the diff assumes unmerged work. Open a
stacked PR only after its parent is up, so the base branch exists on the remote.

---

## PR body template

```markdown
## What this is

Automated maintenance pass over <scope>. No functional change except where noted
under "Behaviour changes" below.

## Commits

Review commit by commit — each is one dimension and independently revertible.

- `<sha>` chore(dead-code): remove 14 unreferenced functions — −610 LOC
- `<sha>` refactor(reports): extract shared filter builder — DUP-01..03
- `<sha>` chore(deps): drop 2 unused, bump 6 patch/minor
- `<sha>` style: apply project formatter to touched files
- `<sha>` fix(security): parameterise report query — SEC-01
- `<sha>` fix(reports): stop swallowing retry errors — CORRECT-02

## Behaviour changes

Everything here changed behaviour deliberately; the rest of the PR did not.

- `SEC-01` — report query now parameterised. Same results, no longer injectable.
- `CORRECT-02` — the retry loop raised nothing on exhaustion and returned partial
  results; it now raises. Callers that relied on the silent partial are affected.

## Verification

- `<test command>` green before and after every commit
- `<lint command>` green
- Coverage <before>% → <after>% (<tool>)

## Measured

| Metric | Before | After | Δ |
|---|---|---|---|
| Code lines (non-blank) | 37,920 | 36,073 | −1,847 |
| Direct dependencies | 24 | 22 | −2 |
| Lint findings | 46 | 12 | −34 |

Not measured: <metric — reason>. (Never quote a number no tool produced.)

## Deferred

Filed as issues, not done here:

- #312 `PRACTICE-01` — split the storage layer (19 files)
- #313 `DEP-05` — SQLAlchemy 2.0 migration

## Gates worth adding

These findings recur unless enforced in CI:

- `STYLE` (34 findings) — no formatter check runs on PRs
- `SEC` — no dependency scanner in the pipeline
```

Trim any section that has nothing in it. An empty "Behaviour changes" heading is worse
than its absence, because a reviewer reads the heading as a claim.

---

## Filing deferred findings as issues

Creating issues is outward-facing, so **list them and ask once** before creating
anything:

> Three findings deferred. File as issues?
> - `PRACTICE-01` — split the storage layer (19 files)
> - `DEP-05` — SQLAlchemy 1.4 → 2.0
> - `PERF-02` — possible N+1 in `list_enrollments`, unmeasured

One issue per finding — a combined "maintenance backlog" issue never gets closed
because it is never entirely done, and it cannot be assigned or prioritised.

File only `deferred` items. **Never file `rejected` ones**: the user decided against
those, and an issue is a request to reconsider.

```bash
gh issue create \
  --title "PRACTICE-01: storage layer has four responsibilities" \
  --body "$(cat <<'EOF'
Found by an automated maintenance pass; deferred as too large for that PR.

**Location:** `internal/storage/` (19 files)

**What:** StorageService handles connection pooling, query building, result mapping,
and cache invalidation. Changes to any one of them touch the same file for unrelated
reasons.

**Why it matters:** cache-invalidation changes currently require understanding the
query builder. Splitting makes each change local.

**Risk:** behaviour-preserving, but wide. Needs the existing storage suite green
throughout, and the suite covers connection handling only thinly.

**Effort:** L — 19 files.

**Deferred because:** a 19-file structural change needs its own PR and its own review.

**Suggested approach:** extract the cache layer first — it has the cleanest seam and
delivers most of the benefit on its own.
EOF
)"
```

Reuse the labels the repo already has rather than inventing a scheme; check with
`gh label list` first. If the project uses Jira instead, the fields are the same — one
issue per finding, with the reason it was deferred.

---

## Session handoff

### When to stop

Stop at a **phase or dimension boundary**, never mid-batch, when:

- context is running short and the remaining work is clearly large;
- a phase completed and what is left is another substantial phase;
- the user answered the Phase 2 question with large items that deserve fresh context.

Degrading with a nearly-full context is worse than pausing: what the last dimension
needs is careful reading, and that is the first thing to suffer.

### Preconditions before handing off

Never hand off mid-flight. A fresh session should find the repository in a state it can
reason about, not a half-applied batch:

1. Everything committed and pushed.
2. Suite green.
3. PR open for what is done, so the delivered work is already reviewable.
4. `.maintenance/plan.md` current — every status, every reason, and what is next.

### The continuation prompt

A new session shares no context, so the prompt has to stand alone: branch, plan file,
what is done, what is next. Keep the detail in `plan.md` and the prompt short — it is a
pointer plus the standing instructions, not a status report.

Write it to `.maintenance/handoff.md` and print it in a fenced block so it can be
copied in one go.

````markdown
Run the next stage of the maintenance pass on this repo.

State from the previous session:
- Branch: `chore/maintenance-2026-09-02` (PR #214, open, suite green)
- Plan: `.maintenance/plan.md` — read it first; it has every finding and status
- Done: RULES, safety net, DEAD, DUP, DEP, STYLE, SEC, CORRECT (8 commits, all pushed)
- Next: PRACTICE-01 (approved — split the storage layer, 19 files), then TEST and DOC

Continue from PRACTICE-01. Same rules as before: apply in verified batches, one commit
per dimension, PRACTICE-01 in its own PR stacked on #214. Do not re-audit the
dimensions already marked done, and do not re-propose anything marked `rejected`.
````

Tell the user plainly what this is: a normal pause, the work so far already delivered
and reviewable, and the next session picking up from the plan. It should not read as a
failure, because it is not one.

If the pause happened because the user's answer to the Phase 2 question is still
outstanding, say so in the prompt — the next session should ask again rather than
assume.
