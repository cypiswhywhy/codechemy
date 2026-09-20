---
name: frame
description: Produce a short design brief before implementing - problem as an outcome, the invariant, the constraints found in the repo, the approach chosen, the approach rejected and why, blast radius, and how we will know it worked. Use when the change alters a published contract or API, crosses a module boundary, introduces a dependency or a data migration, or is hard to undo; and on "/frame", "design this first", "how should we build this", "what are the options", "think before coding". Refuses and hands back when the change is small enough to just write.
---

# Frame

A senior engineer's edge is mostly spent before the first line: on deciding what to build and
which shape it takes. This skill makes that step explicit and cheap. It produces **one screen
of brief**, gets one decision from the user, and hands off to implementation.

It writes no code and creates no file unless the repo already keeps decision records.

## Step 1 — Check it is worth framing

Run this first and be willing to stop here. Framing a change that did not need it is pure cost,
and doing it by reflex is how the skill becomes something the user turns off.

Frame when **any** of these holds:

- it changes a published contract - an API, CLI flag, config key, event, schema, exported symbol
- the work spans modules that are separately owned, tested or deployed
- it adds a dependency, a data migration, or anything with state that outlives a deploy
- undoing it after release costs more than a revert
- the user asked for options, or two readings of the request lead to different work

Otherwise say in one line why not - "single module, reversible, one obvious shape" - and go
write the code. The practice `05-understand-first` already covers the small case in four lines.

**If the repo uses OpenSpec** (an `openspec/` directory), this is `/opsx:propose`'s job. Say so
and defer to it rather than producing a second, competing artifact.

## Step 2 — Gather, do not guess

The value of the brief is entirely in whether its constraints are real. So each one gets
evidence before it is written down:

1. **Read the code the change lands in**, not just around it. Name the files.
2. **Find prior art** in this repo: an existing feature of the same kind, and how it is shaped.
   That shape is a constraint even where nothing documents it.
3. **Find the recorded decisions** - `docs/internals`, ADRs, `openspec/`, `CLAUDE.md`,
   `CONTRIBUTING.md`. A decision already made is not yours to re-open inside a feature.
4. **Establish the current behaviour** where the change touches something that exists. If you
   cannot say what it does today, you cannot say what your change alters.

Never write a constraint you cannot point at. A brief built from plausible-sounding assumptions
is worse than no brief, because the user reviews it as though it were findings.

## Step 3 — Write the brief

One screen. This shape, in this order, and nothing longer:

```markdown
**Problem** - <the outcome someone wants, one line, no solution in it>
**Invariant** - <what is true now and must still be true after>
**Constraints** - <2-4 lines, each citing a file, a decision record, or the user's own words>

**Approach** - <3-6 lines: the shape, the seam it uses, what it touches>
**Rejected: <name>** - <one line> because <one line>.

**Blast radius** - <files/modules; the public surface it changes; migration and rollback>
**How we will know** - <the test or measurement that shows it worked>
**Open** - <at most two questions, each with your recommendation>
```

Rules that keep it honest:

- **At least one rejected approach, with its reason.** A brief that considered one option did
  not design anything, it described the first idea. If the alternative really is unthinkable,
  say what makes it so - that is the constraint, and it belongs in `Constraints`.
- **The problem line contains no solution.** "Users lose their draft when the tab closes" is a
  problem; "add localStorage persistence" is the approach with the problem hidden inside it.
- **"How we will know" is a test you could write, or a number you could read** - not "it works".
- **Two open questions maximum**, each with your recommendation attached, so the user can answer
  with a word. More than two means you did step 2 too shallowly.
- **No estimates in the brief** unless the user asked for one.
- If it will not fit on a screen, the change holds more than one decision. Say which decisions
  are in it and frame the first one; the rest follow their own briefs.

## Step 4 — One decision, then go

Ask once, with `AskUserQuestion`: the chosen approach against the rejected one, plus any open
question. Carry your recommendation in the first option.

Then, before implementing, name the landing points the way `20-small-increments` requires - the
groups this will land in, each one shippable on its own - and start on the first. Where the
repo uses OpenSpec and the change is large, `/apply-increment` takes it from here.

## Step 5 — Record it only if it outlives the change

Most briefs are scaffolding and belong in the conversation. Write one down only when the
decision will be asked about again - and then into whatever the repo already keeps: an ADR
under `docs/internals`, an OpenSpec design, the format the neighbours use. Do not introduce a
new location or a new template for it; if the repo records nothing, the commit message body is
the right home for the two lines that matter.

## Rules

- Never write production code in this skill. It ends at an agreed approach.
- Never invent a constraint, a requirement or a prior decision. Cite, or leave it out.
- Never re-open a decision the repo already recorded. Name it as a constraint; if it is the
  thing blocking a good design, say so as an open question and let the user decide.
- Keep the user's framing where it is adequate. Reframing what the user already stated clearly
  is not design work.
- One screen, one decision, no file unless step 5 applies.
