SKILLS_SRC := claude-code/skills
SKILLS_DEST := $(HOME)/.claude/skills

.PHONY: install-skills
install-skills:
	@mkdir -p "$(SKILLS_DEST)"
	@# Prune only the links this target owns (those pointing into SKILLS_SRC) whose
	@# target has gone, so renaming or deleting a skill leaves no dangling link.
	@# Links to other sources (e.g. docschemy) are never touched, since this target
	@# could not recreate them.
	@for link in "$(SKILLS_DEST)"/*; do \
		[ -L "$$link" ] || continue; \
		case "$$(readlink "$$link")" in \
			"$(CURDIR)/$(SKILLS_SRC)/"*) \
				if [ ! -e "$$link" ]; then \
					rm -f "$$link"; \
					echo "pruned    $$(basename "$$link") (target gone)"; \
				fi ;; \
		esac; \
	done
	@for skill in $(SKILLS_SRC)/*/; do \
		[ -f "$$skill/SKILL.md" ] || continue; \
		name=$$(basename "$$skill"); \
		ln -sfn "$(CURDIR)/$(SKILLS_SRC)/$$name" "$(SKILLS_DEST)/$$name"; \
		echo "installed $$name -> $(SKILLS_DEST)/$$name"; \
	done
