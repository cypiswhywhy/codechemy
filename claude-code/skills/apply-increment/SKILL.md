---
name: apply-increment
description: Implement the next small increment of an OpenSpec change as its own commit and PR, instead of the whole tasks.md in one run. Trigger on "/apply-increment", "apply the next increment", "implement the next task group", "ship this change in small PRs", or when a change should land as one PR per shippable increment instead of one run. Also seeds the increment rules into the project's openspec/config.yaml once, with the user.
---

# Apply increment

`/opsx:apply` walks the whole task list of an OpenSpec change in one run, which is how a
single PR ends up with thousands of changed lines. This skill implements **one task group**,
lands it as its own reviewable PR, and stops. Run it again after the PR merges for the next
group. It reuses OpenSpec's own artifacts and CLI; it does not replace `/opsx:propose`,
`/opsx:archive` or the change's specs.

Requirements: the `openspec` CLI, a clean working tree, and either the `/push` skill or `gh`.

## Steps

1. **Select the change** the way `/opsx:apply` does. Use the name given
   (`/apply-increment <change>`), else infer it from the conversation, else auto-select the only
   active change, else run `openspec list --json` and ask. Announce `Using change: <name>`.

2. **Seed the increment rules, once per project.** Read `openspec/config.yaml`. If it has no
   `operations.apply.guidance` entry mentioning "one task group per run", show the user the
   snippet below and ask a single question: add it, skip for now, or never (then add
   `# apply-increment: declined` to the file so this step stays silent). Do not edit the file
   without the answer. With the entry in place, plain `/opsx:apply` also reads it, and
   `/opsx:propose` shapes new task lists into increments from the start.

   ```yaml
   rules:
     tasks:
       - Group tasks under `## N. <increment name>` headings so that each group is one
         independently shippable, reviewable PR: one piece of value, complete and useful on its
         own once merged. Size follows from the value, so a group may be 40 changed lines or
         1000; never split one piece of value across groups to make them smaller, and never
         bundle two of them to save a round trip.
         Put behaviour-preserving refactors in their own group, before the feature they enable.
   operations:
     apply:
       guidance:
         - Implement one task group per run. When the group's tasks are done and verified,
           stop, commit (Conventional Commits) and hand off to /push (or /apply-increment);
           do not start the next group in the same run.
         - Within the files each task touches, leave the code smaller than you found it and
           report the diff shape (+N / -M) in the summary.
   ```

   Merge into existing `rules.tasks` / `operations.apply.guidance` lists; never replace them.

3. **Read the change.** `openspec status --change "<name>" --json`, then
   `openspec instructions apply --change "<name>" --json`. Handle `blocked` and `all_done`
   exactly as `/opsx:apply` does. Read every file in `contextFiles`. Treat `context` as
   required input and `operationGuidance` as advisory, as that command specifies.

4. **Find the next increment.** Task groups are the `## N. <name>` (or `### `) headings in the
   tasks file; the next increment is the first group with an unchecked task. If the tasks file
   has no groups, or the next group holds more than one piece of value (two features, unrelated
   subsystems), or less than one (its value only works once a later group lands), propose a
   regrouping of the *tasks file only* (no code), splitting or merging groups; show it, and
   apply it when the user agrees. Size is not a seam: a large group that delivers one piece of
   value stays one increment. Never regroup silently. Announce
   `Increment k/m: <group name> (t tasks)`.

5. **Branch.** The working tree must be clean; if it is not, stop and say what is pending.
   On the default branch, create `<type>/<change>-<k>-<slug>` from it. On another branch, stay
   on it and say so. Baseline the tests once (`## Maintenance toolbox` in CLAUDE.md, else the
   project's usual command) so a later failure is attributable to this increment.

6. **Implement the group and nothing else.** Follow `/opsx:apply`'s guardrails per task:
   pause on ambiguity, surface added scope instead of absorbing it, tick `- [ ]` → `- [x]` only
   when a task's specified behaviour is fully implemented. A task from a later group that
   becomes tempting stays in its group. Apply the leave-it-smaller contract to the files
   touched. Run tests and lint; green is required to proceed.

7. **Land it.** Commit with Conventional Commits, in as many commits as there are coherent
   steps (refactor first). Then hand off to `/push` when that skill is available; otherwise
   `git push -u origin HEAD` and `gh pr create` with the title
   `<type>(<change>): <group name> (increment k/m)` and a body that lists the group's tasks
   verbatim, links the change directory, and states how many increments remain.

8. **Stop and report.** Increment done, the diff shape (`+N / -M`, files), tests run, PR URL,
   remaining groups by name, and the next command. Offer two: `/apply-increment <change>` after
   this PR merges (or immediately on a stacked branch, if the user prefers; say that stacking is
   the default only when they ask for it), and `/apply-all-increments <change>`, which always
   starts from a fresh main and walks through the remaining groups and the archive without
   re-invoking. If the group was the last one, suggest `/opsx:archive`.

## Rules

- One group per run. Never start the next group in the same run, even when it is small.
- Never widen a group during implementation; propose the change to the tasks file instead.
- The tasks file is the single progress record; a task is done only when checked there.
- Do not edit `openspec/config.yaml` without the user's answer in step 2, and ask only once.
- Keep every increment behaviour-complete for its tasks; "half of task 3.2" is never a
  landing point. A group too large for one run is a regrouping only when it holds more than one
  shippable piece of value; otherwise it is implemented whole.
- Fewer complete increments beat more partial ones. Never create a group whose PR nobody could
  merge and use on its own, and never treat the number of PRs as a measure of progress.
