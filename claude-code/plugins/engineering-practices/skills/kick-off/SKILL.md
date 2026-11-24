---
name: kick-off
description: Record how this project wants Claude to work - which code reviewer /push uses first (GitHub Copilot or the local /code-review), whether a plan needs the user's approval before implementation starts, and whether work is tracked in Jira (read through the Atlassian MCP server, with ticket statuses moved as the work progresses) - as a `## Project workflow` section in the project's CLAUDE.md or CLAUDE.local.md, which the other skills read. Detects what the repo already says (OpenSpec) instead of asking. Trigger on "/kick-off", "kick off this project", "set up my preferences for this project", "always ask before implementing here", "use the local review in this repo", "we track this in Jira".
---

# Kick-off

Some choices differ per project and cannot be read from the code: which reviewer gates a PR,
whether the user wants to approve a plan before any code is written, whether the work is
tracked in Jira. This skill asks them once and records the answers as a `## Project workflow`
section, which every later session loads with the project's instructions.

A missing section, or a missing line in it, means the default below, which is how the plugin
behaves without this skill. So no other skill needs `/kick-off` to have run.

| Line | Values | Default | Read by |
|---|---|---|---|
| `Review` | `copilot`, `local` | `copilot` | `/push`: `local` skips Copilot and runs the one-pass local `/code-review` |
| `Plan approval` | `auto`, `ask` | `auto` | every session outside the OpenSpec apply skills, `/frame` |
| `Jira` | `off`, or a project key with its status names | `off` | `/apply-increment`, `/push`, `/apply-all-increments` |

Do not ask what the repo answers. An `openspec/` directory means the project uses OpenSpec; the
skills that care detect it themselves, so it is reported, not recorded.

## Steps

1. **Read what is recorded.** Look for `## Project workflow` in `CLAUDE.md` and
   `CLAUDE.local.md` at the git root. If one exists, show its current values; the questions
   in step 3 then change them rather than start over.

2. **Detect.** Report in one line, without asking: OpenSpec, `openspec/` present or not.

3. **Ask once**, with one `AskUserQuestion` call holding these questions. Put the current value,
   or the default when nothing is recorded, first:
   - **Review**: `copilot` (an independent model reviews; costs premium requests and a 4-6
     minute wait per cycle) or `local` (the same model in a fresh context, one pass, no wait). `local`
     does not stop a ruleset that auto-requests Copilot; say so if one exists.
   - **Plan approval**: `auto` (show the plan and go on) or `ask` (show the plan and wait for a
     yes before editing code).
   - **Jira**: `off` or `on`.
   - **Where**: `CLAUDE.md` (committed; the whole team gets these settings) or
     `CLAUDE.local.md` (only this user; must be git-ignored, add it to `.gitignore` if it is
     not). Keep the file the section is already in, if any.

   Without `AskUserQuestion` (`claude -p`, a subagent), write nothing and report the defaults
   and what was detected.

4. **Jira details**, only when the answer was `on`. Jira is reached through the Atlassian MCP
   server's tools. If the session only has its `authenticate` tool, run it and let the user
   finish the sign-in; if there is no Atlassian server at all, record `Jira: off` and say that
   connecting it and re-running `/kick-off` turns it on. Then:
   - List the projects the user can see and the statuses of that project's workflow (from the
     transitions of a recent issue).
   - Ask one more `AskUserQuestion` call: the project key, and which status means each of
     `start` (work begun), `review` (PR open) and `done` (merged and archived). Propose the
     closest names, such as `In Progress`, `In Review`, `Done`.

5. **Write the section.** Append it to the chosen file, or replace it in place, using this
   shape and nothing longer. Write every line, defaults included, so the reader sees each
   choice was made:

   ```markdown
   ## Project workflow
   <!-- project-workflow: recorded YYYY-MM-DD by /kick-off -->
   - Review: copilot
   - Plan approval: ask - before editing code, show a short plan (what changes, in which files,
     which tests prove it) and wait for the user's yes. OpenSpec apply skills skip this: the
     change is the approved plan. A session that cannot ask (`claude -p`, CI, a subagent)
     states the plan and goes on.
   - Jira: PROJ - start "In Progress", review "In Review", done "Done"
   ```

   With `Plan approval: auto`, the line is just `- Plan approval: auto`; with Jira off,
   `- Jira: off`. The `ask` line carries its own instruction because the section is loaded into
   every session, where it is the only thing that makes the session wait.

6. **Finish.** List the recorded values, the file, and what was detected. Leave the edit in the
   working tree unless the user's workflow commits CLAUDE.md changes as a matter of course.

## Rules

- One question call in step 3, plus one in step 4 when Jira is on. Everything else is detection.
- Never write a value the user did not choose. A skipped question keeps the recorded value, or
  the default when none is recorded.
- Record only lines from the table above. A preference no skill reads is noise in every session.
