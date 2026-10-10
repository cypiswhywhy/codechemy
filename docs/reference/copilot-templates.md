# Copilot review templates

In `github-copilot/instructions_templates/`. How to install them:
[../usage/copilot-review.md](../usage/copilot-review.md).

| Template | Copy to | What it is |
|---|---|---|
| [`copilot-instructions.md`](../../github-copilot/instructions_templates/copilot-instructions.md) | `.github/copilot-instructions.md` | repository-wide review instructions; fill in the placeholders |
| [`python-package.instructions.md`](../../github-copilot/instructions_templates/python-package.instructions.md) | `.github/instructions/` | path-scoped instructions for a Python package's source tree; set `applyTo` |
| [`openspec.instructions.md`](../../github-copilot/instructions_templates/openspec.instructions.md) | `.github/instructions/` | path-scoped instructions for OpenSpec change artifacts (`openspec/**`) |
| [`code-review-lessons.md`](../../github-copilot/instructions_templates/code-review-lessons.md) | `.claude/code-review-lessons.md` | a shared tally of recurring mistakes caught in review |

**`openspec.instructions.md`.** OpenSpec artifacts are planning documents rather than code,
so the repository-wide rules about tests and performance do not fit them. The template
redirects review to what goes wrong in a spec — anchors naming symbols that do not exist,
claims the code cannot support, a task with no normative backing, an absolute with a
counterexample — and asks for one comment per class of finding rather than one per
occurrence, because the same claim is normally restated across the artifacts.

**`code-review-lessons.md`.** `/push` appends to it and proposes a rule for `CLAUDE.md` once
a class of mistake has recurred in three independent PRs.
