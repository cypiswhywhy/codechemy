# Set up automated Copilot code review

`/push` uses GitHub Copilot as its code reviewer, and falls back to a local `/code-review` pass
when Copilot is not available. To make Copilot review a repository's pull requests:

1. In the repository, open **Settings → Rules → Rulesets** and create a branch ruleset.
2. Enable **Automatically request Copilot code review**. Optionally also:
   - **Review new pushes** — reviews again when new commits are pushed.
   - **Review draft pull requests** — early feedback before a human reviews.
3. Copy [`copilot-instructions.md`](../../github-copilot/instructions_templates/copilot-instructions.md)
   to the repository's `.github/` folder and fill in the placeholders.
4. Optionally add path-scoped instructions: copy a template to `.github/instructions/` and set
   its `applyTo` globs.
5. Optionally start a lessons ledger: copy
   [`code-review-lessons.md`](../../github-copilot/instructions_templates/code-review-lessons.md)
   to `.claude/code-review-lessons.md`.

What each template is for: [../reference/copilot-templates.md](../reference/copilot-templates.md).
GitHub's guide to repository instructions:
https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions
