# Code review lessons

Recurring classes of mistake caught by automated code review in this repository.
Appended by the `push` skill (Step 10) and shared by everyone who runs it, so the
tally reflects the project's evidence rather than one person's.

One `##` section per *class* of mistake — the pattern, never the individual fix.
One bullet per occurrence: date, PR URL, and a short phrase naming the instance.
Add a bullet to the existing section when a class recurs; do not open a second
section for it.

Three occurrences from independent PRs is the threshold for proposing a preventive
rule in `CLAUDE.md` (project-specific) or `~/.claude/CLAUDE.md` (general). A single
occurrence is noise — record it, but do not legislate from it.

Only comments that were **addressed** belong here. A comment that was declined is
evidence about the reviewer, not about us, and belongs in
`.github/copilot-instructions.md` instead.

<!-- Delete the example below once the first real entry is recorded. -->

## Example — optional config fields assumed present

Reading an optional setting without checking that it exists, so a run on a default
config gets `undefined` instead of the intended fallback.

- 2026-01-01 — https://github.com/<owner>/<repo>/pull/1 — `cfg.timeout` read directly in `parser.ts`
