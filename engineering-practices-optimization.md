# engineering-practices: optimizing the startup prompt

## TL;DR

1. Keep only `05-understand-first` always on; turn the other seven practices into one-line
   pointers to the skills that apply them.
2. Deliver code-shape rules (say less, leave it smaller) when they become relevant, from hooks,
   instead of at session start.
3. Tone down the "OVERRIDE every default" preamble so the practices don't compete with the
   task's own firm rules.

**Working hypothesis (not proven):** an 8.9k-character always-on block of general process rules,
framed as overriding every default, takes the model's attention away from domain reasoning.

## The current startup prompt

`hooks/practices.py` concatenates a preamble and every `practices/*.md` file at SessionStart:
8,969 chars, 1,566 words, about 2.2k tokens.

| File | Chars | Useful in a headless, single-shot session? |
|---|---:|---|
| `05-understand-first.md` | 1,022 | yes: closest thing to what the bad runs missed |
| `10-leave-it-smaller.md` | 1,470 | partly; only relevant while editing |
| `15-reuse-before-adding.md` | 925 | partly; only relevant while adding code |
| `20-small-increments.md` | 1,093 | mostly no: PRs, review cycles, branches |
| `30-test-driven.md` | 1,160 | yes |
| `35-correct-by-construction.md` | 1,290 | yes, but only when writing code |
| `40-say-less.md` | 1,001 | only when writing code; the Stop hook already enforces it |
| `45-write-plainly.md` | 792 | no: there is no reader in a headless run |

## Recommendations

### 1. Split into an always-on core and on-demand practices (do first)

- Add a frontmatter key to each `practices/*.md`, e.g. `tier: core` or `tier: on-demand`.
- `hooks/practices.py` prints `core` files in full and each `on-demand` file as one line: its
  title, a one-sentence rule and where the detail lives.
- Suggested core: `05-understand-first`, `30-test-driven`.
- Put the detail where it is used, in skills the plugin already ships:

  | Practice | Move detail into |
  |---|---|
  | `10-leave-it-smaller`, `15-reuse-before-adding`, `40-say-less` | `skills/self-review` (it already reviews the diff) |
  | `20-small-increments` | `skills/apply-increment`, `skills/push` |
  | `35-correct-by-construction` | `skills/self-review` checklist |
  | `45-write-plainly` | `skills/push` (PR/commit bodies); one core line for chat replies |

- Target size: under ~2,500 chars at session start, about a third of today.
- Update `hooks/test_practices.py` so it asserts the tiering. A test that only checks "all files
  are printed" will still pass on the old behaviour.

### 2. Deliver code-shape rules when they apply (do second)

- Add a `PostToolUse` hook on `Edit|Write` that returns the relevant one-paragraph rule
  (say less, leave it smaller, correct by construction) as `additionalContext`. Send it once per
  session, or once per file, so it doesn't repeat on every edit.
- The `Stop` hook (`hooks/leave_it_smaller.py stop`) already measures the change. Keep it as the
  enforcement point, so the startup text doesn't need to repeat what it checks.
- Check the exact hook output schema against the Claude Code version you pin before relying on
  it.

### 3. Tone down the preamble (small, do with 1)

- Current: "Standing instructions for this and every session … where they conflict with a
  default behaviour they OVERRIDE it."
- Problem: brownfield tasks come with their own firm rules. The ledgerline ticket says the
  documented rule wins, and sterling output must stay byte-for-byte identical. A blanket override
  frames the practices as the top priority, ahead of the task.
- Suggested: "Defaults for how to work. The task's own requirements and the project's
  documented rules come first; these practices decide how, not what."
- Check `10-leave-it-smaller` against this too: "remove compatibility shims" and "net-negative
  diff is preferred" can conflict with "behaviour must be indistinguishable". The round shows no
  harm here (regression cases passed 48–49 of 49 in every engineering-practices run, the same
  range as the baseline), so this is low priority.

### 4. Optional: make domain rules an explicit framing step (test separately)

- In `05-understand-first` and `skills/frame` Step 3, add one line: when the change lands in a
  domain with established rules (money/accounting, time zones, units, protocols), write the
  domain rule down before the design, and add a test for it.
- This targets exactly what separated good runs from bad ones. Overfitting risk: it reads as
  tuning the plugin to this benchmark. Ship it only if it also holds on a task it wasn't
  written for.

