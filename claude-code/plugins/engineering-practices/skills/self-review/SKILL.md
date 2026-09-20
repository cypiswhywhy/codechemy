---
name: self-review
description: Review your own change before anyone else sees it - the claims it makes and the code it adds - and fold the fixes into the commits rather than into a review cycle. Runs against the working tree, the staged change, or the branch. Use on "/self-review", "check your own work", "review this before I commit", before the first push of a branch, and before handing a change back. /push runs it automatically at Step 0.
---

# Self-review

The cheapest defect is the one caught before anyone else reads it. A finding that reaches an
automated reviewer costs a full cycle - triage, a fix, a re-push, and minutes of waiting - and
a finding that reaches a person costs their attention, which is scarcer still. Every item here
is mechanical: it is checkable against the tree rather than a matter of judgment, which is what
makes it worth running every time.

This skill only reads and fixes. It does not commit, push or open anything.

## Step 1 — Establish the diff and the gate

1. **Get the actual diff**, never your memory of it: `git diff` for the working tree,
   `git diff --staged`, or `git diff <default-branch>...HEAD` for the branch. Review what is
   there; memory omits exactly the drive-by edits worth checking.
2. **Run the project's gates first** - the tests, and whatever its `CLAUDE.md` records under
   `## Maintenance toolbox`. A review pass over a red suite is spent on something the command
   already knew. If either is missing, say so and continue.

## Step 2 — The claims the change makes

These produce most of what an automated reviewer sends back, and every one of them is
answerable by grepping the tree. They apply to prose and commit messages as much as to code.

1. **Every symbol named exists.** Grep for each class, method, function, field, flag and file
   path the diff mentions. A name that reads like the right one is the commonest failure: it
   came from what the thing *ought* to be called, not from the tree.
2. **Every line number and anchor still resolves.** They drift, and a citation the same change
   moves is dead on arrival. Prefer the symbol over the line.
3. **Every absolute has been checked against its counterexample.** For each "only", "never",
   "always", "every", "cannot" in the diff, find the case that would contradict it. If one
   exists, name it in the same sentence or drop the absolute.
4. **No claim asserts what the code cannot observe.** A record written before an operation
   cannot attest to its outcome; a pre-flight check cannot prove delivery; a count of what was
   attempted is not a count of what succeeded.
5. **A new rule applies at every site that asks the same question.** Grep for the old predicate
   across the tree, not only the call site you were editing.
6. **The summary is true.** Re-read what you are about to tell the user against the diff. An
   overstated summary is a false claim with a larger audience than any comment.

## Step 3 — The code the change adds

One pass, in this order. Each maps to a practice, which carries the reasoning.

1. **Does it already exist?** Grep for the concept rather than the name (`normali[sz]`, `slug`,
   `retry`) before keeping any helper, validator, formatter or constant you added. A second
   call site means generalise the first, not copy it. ("Reuse before adding")
2. **Did a new path supersede an old one still in the tree?** Delete the old one here.
   ("Leave the code smaller than you found it")
3. **What did you leave behind?** Dead code, unused imports and parameters, a flag with one
   caller, a comment or docstring restating the line under it, defensive code for a case that
   cannot happen. Prove each removal before making it. ("Say less in the code")
4. **Where does untrusted data enter, and what happens on the error path?** Validation at the
   boundary, errors propagated with context rather than swallowed, resources released on the
   failure path too, anything retriable made safe to run twice. ("Correct by construction")
5. **Do the tests assert the behaviour, or a proxy for it?** A key being present is not its
   value being right; a call being made is not the effect happening. A test that cannot fail
   against the old behaviour is asserting nothing - check one by reverting the fix in your head
   and asking what turns red. ("Test-driven by default")

## Step 4 — Fix and report

Fold every fix into the commits being reviewed rather than stacking a "fix review findings"
commit on top - at this stage nobody has seen the originals, so there is no history to
preserve. Do not open a PR to fix your own findings.

Report in three lines: what you checked, what you found and fixed, and the diff shape
(`+N / -M`, files). Finding nothing is a normal outcome; say so rather than manufacturing a
finding.

## Rules

- Never commit, push, or open a PR from this skill.
- Check against the tree, not against your reasoning. "I remember writing that helper" is not
  a grep.
- Do not start a refactor here. A finding too large to fold in is a note for the summary, and
  its own change afterwards.
- This does not replace review by someone else. It removes the findings that would have eaten
  the cycles, so the cycles that do run are spent on what you could not have found yourself.
