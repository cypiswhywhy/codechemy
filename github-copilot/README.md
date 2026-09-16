# Automated GH code reviews setup

## GH repository setup
In Repository → Settings → Rules → Rulesets, create a branch ruleset and enable
“Automatically request Copilot codereview”.

You can also enable:
- **Review new pushes** – reruns review when new commits are pushed.
- **Review draft pull requests** – useful for early feedback before human review.

## Code review configuration
Repository-wide instructions, just copy `copilot-instructions.md` to the `.github` folder in a given repository.

Setting up path or file-type specific instructions: https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions#creating-path-specific-custom-instructions

Path-scoped templates in `instructions_templates/` — copy to
`.github/instructions/` and fill in the `applyTo` globs:

- `python-package.instructions.md` — a Python package's source tree.
- `openspec.instructions.md` — OpenSpec change artifacts (`openspec/**`). These are
  planning documents rather than code, so the repository-wide rules about tests and
  performance do not fit them. It redirects review to what actually goes wrong in a
  spec — anchors naming symbols that do not exist, claims the code cannot support,
  a task with no normative backing, an absolute with a counterexample — and asks for
  one comment per class of finding rather than one per occurrence, because the same
  claim is normally restated across all four artifacts.

`code-review-lessons.md` is a different kind of template — copy it to
`.claude/code-review-lessons.md` in a repository to start a shared tally of
recurring mistakes caught in review. The `push` skill appends to it and promotes a
class to `CLAUDE.md` once it has recurred three times.

This file contains instructions for Copilot to follow when performing code reviews.

# References
- https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions