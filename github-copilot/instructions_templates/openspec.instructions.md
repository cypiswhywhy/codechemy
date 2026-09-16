---
applyTo:
  - "openspec/**"
---

These files are an OpenSpec change: a `proposal.md` (why and what), a `design.md`
(decisions and rejected alternatives), one or more spec deltas under `specs/`
(normative requirements and scenarios), and a `tasks.md` (the implementation
checklist). They are planning artifacts. The code they describe is usually not in the
same pull request, and the change is archived once it ships.

Review them as a specification, not as prose. The repository-wide instructions about
correctness, tests and performance describe code and mostly do not apply here.

## What to review for

- **A symbol, path, line anchor or command that does not exist.** These files name
  the code they will change. A method, class, field, flag or file that is not in the
  tree sends the implementer somewhere that is not there. This is the single
  highest-value finding in an OpenSpec change — check every anchor.
- **A claim the code cannot support.** Verify assertions about existing behaviour
  against the tree. Pay particular attention to anything described as recording,
  proving or guaranteeing an outcome: a value captured before an operation cannot
  attest to its result.
- **A requirement contradicting another requirement**, or a scenario contradicting
  the requirement it sits under.
- **A `tasks.md` item with no normative backing.** If a task requires behaviour the
  spec delta does not make normative, an implementation can satisfy the spec and
  still fail the task — say which side is missing.
- **A spec delta that permits what the design forbids.** The spec is the contract;
  if a conforming implementation could do the thing the design rules out, the spec
  has a gap.
- **An absolute with a counterexample in the same change** — "only", "never",
  "always", "every", "cannot". Name the contradicting case.
- **A task ordered before the task it depends on**, and a task whose stated
  verification cannot produce the evidence it asks for.
- **A refusal, state or invariant defined asymmetrically**, so that the mirror case
  falls through: an explicit value compared against an explicit value while an
  omitted one is treated as absent rather than as its default.

## What not to review for

- Wording, tone, structure and formatting, unless meaning changes.
- The merits of a decision the `design.md` records with its alternatives. Reviewing
  whether the chosen option was right is out of scope; reviewing whether the document
  describes it consistently is in scope.
- Test coverage, performance and observability. There is no code here.
- Anything already corrected in a later commit on the branch. Check the current file
  content before reporting, and do not re-report a finding whose quoted text is no
  longer present.

## How to report

One comment per *class* of finding, listing every file and line where it occurs —
not one comment per occurrence. The same claim is typically restated across the
proposal, the design, the spec delta and the tasks, so a per-site comment turns one
defect into four review rounds. If a defect appears in more than one file, say so in
the one comment.
