---
name: apply-all-increments
description: Drive an OpenSpec change from its current state all the way to main, one increment at a time. Revalidates the change against today's main, then for each remaining task group runs /apply-increment, hands the PR to /push, waits for the user to merge, and continues; when every group is on main it archives the change and reports. Trigger on "/apply-all-increments", "apply all increments", "ship the whole change", "take this change to main", or when the user wants to be walked through every increment instead of re-invoking /apply-increment after each merge.
---

# Apply all increments

`/apply-increment` lands one task group and stops; the user re-invokes it after each merge.
This skill is the loop around it. It walks the user through the entire change, from "is this
proposal still valid" to "archived", and the user's only manual step is merging each PR.
Everything else is delegated: the increment to `/apply-increment`, the PR and its review to
`/push`, the archive to `/opsx:archive`. Nothing is held in the session: ticked tasks are on
main, open PRs are on GitHub and merged ones are in the run log, so an interrupted or compacted
run resumes where it stopped and still reports every increment.

Requirements: the `openspec` CLI, `gh`, the `/apply-increment` and `/push` skills, and a clean
working tree.

## Steps

1. **Select the change** the way `/apply-increment` does: the name given
   (`/apply-all-increments <change>`), else inferred from the conversation, else the only active
   change, else `openspec list --json` and ask. Announce `Using change: <name>`.

2. **Revalidate the change.** Main has usually moved since the proposal was written and nothing
   else re-checks it. Before touching code:
   - `git fetch origin`, check out the default branch and fast-forward it. The working tree must
     be clean; if it is not, stop and say what is pending.
   - `openspec validate "<name>" --strict --json` must pass and
     `openspec status --change "<name>" --json` must show every artifact done. Otherwise stop and
     point to `/opsx:continue`.
   - Read the proposal, design, specs and tasks. List the files, modules and dependencies they
     name and check each against the tree. Look for renamed or deleted files, a dependency that
     is gone, a task whose work already landed another way, and a group that no longer maps to
     one shippable piece of value.
     `git log --oneline <last commit under openspec/changes/<name>>..origin/main
     -- <paths named in design>` shows what changed underneath the design.
   - Report `Change still valid` or the discrepancies, each with a proposed edit to the tasks or
     design file. Apply the edits the user agrees to on a branch
     `docs/<change>-revalidate`, commit them as `docs(<change>): revalidate against main`, and
     stay on that branch so step 4 builds on it. Never edit code here.
   - Announce `Plan: m increments remaining: <group names>`. Each increment is one PR round trip:
     implementation, a Copilot review of a few minutes, and the user's merge.

3. **Detect an in-flight increment.** `gh pr list --state open --search "<change>" --json
   number,headRefName,url`. An open PR on a `*/<change>-<k>-*` branch means a previous run stopped
   before its merge: check the branch out and continue at step 5 with that PR instead of
   implementing the group again.

4. **Apply the next increment.** Invoke `/apply-increment <change>`. It seeds the config once,
   picks the next group, branches, implements, commits and hands off to `/push`. Its pauses are
   this skill's pauses: when it stops on ambiguity or proposes a regrouping, wait for the user,
   then resume the loop; do not answer on their behalf.

5. **Land the PR.** `/push` ends with the PR green and its URL. Ask exactly one question with
   AskUserQuestion: `PR #n (increment k/m: <group name>) is green. Merge it, then continue.` with
   the options **Merged, continue** and **Stop here**. Never merge it yourself. On continue,
   verify with `gh pr view <n> --json state,mergedAt`; if it is not merged, say so and ask once
   more; if it is still not merged, stop and report.

6. **Return to main.** Check out the default branch, `git pull --ff-only`, delete the local
   increment branch. Append the merged PR to the run log,
   `.git/apply-all-increments/<change>.log` (create the directory), one line of
   `<k/m, or "archive"> | <group name> | <PR url> | +N / -M`. It lives under `.git` so it never
   dirties the working tree that step 4 requires clean, and never needs a `.gitignore` entry.
   Announce `Increment k/m merged: <group name>. Next: <group name>` and go to step 4. When no
   unchecked task remains, go to step 7.

7. **Archive.** Every group is on main, so the archive gets its own branch,
   `chore/<change>-archive`. Invoke `/opsx:archive <change>` when it is available, since it also
   syncs the delta specs into the main specs; otherwise `openspec archive "<name>"`. Pass its
   questions (spec sync, warnings) through to the user; do not decide them. Commit as
   `chore(<change>): archive change`, hand off to `/push`, ask for the merge as in step 5, return
   to main as in step 6.

8. **Summary.** Read the run log and take the per-increment lines from it rather than from the
   session, so a compacted run reports as completely as an uninterrupted one. Change name; one
   line per increment with group name, PR URL and diff shape; the total diff shape; the archive
   location and spec sync status; artifact edits made in step 2; anything declined or skipped
   along the way. Then delete the run log. The change is on main and archived, so there is no
   next command to give.

## Stopping and resuming

- Stop when the user picks **Stop here**, when `/apply-increment` pauses and the user does not
  resolve it, when `/push` reaches its review cap, or when a PR is still unmerged after the second
  ask. Report exactly where: which increment, which step, what the user must do, and that
  `/apply-all-increments <change>` resumes from there.
- Step 3 makes resuming safe: the tasks file on main says which groups are done, GitHub says
  which PR is waiting and the run log says what each merged increment was, so a fresh session or
  a compacted context loses nothing. A resumed run appends to the existing log.

## Rules

- Every code decision belongs to `/apply-increment` and every review decision to `/push`. This
  skill writes no code and triages no review comment; it only sequences those two skills.
- One question per PR: the merge. Everything else it can find out with `gh`, `git` and
  `openspec`.
- Never merge, never push to the default branch, never skip `/push`.
- The archive is its own PR, never bundled into the last increment.
- Revalidation edits the change's artifacts only, only with the user's agreement, and only
  before the first increment; later drift is `/apply-increment`'s "surface added scope" pause.
