SKILLS_SRC := claude-code/skills
SKILLS_DEST := $(HOME)/.claude/skills

# What each skill shells out to, as `skill:cmd,cmd`.
PREREQS := \
	push:git,gh \
	codebase-maintenance:git,gh,python3 \
	claude-customizations:python3 \
	apply-increment:git,gh,openspec \
	apply-all-increments:git,gh,openspec

.PHONY: check
check:
	@missing=""; \
	for entry in $(PREREQS); do \
		lack=""; \
		for cmd in $$(echo "$${entry#*:}" | tr ',' ' '); do \
			command -v "$$cmd" >/dev/null 2>&1 || lack="$$lack $$cmd"; \
		done; \
		if [ -n "$$lack" ]; then \
			echo "MISSING   $${entry%%:*} needs:$$lack"; \
			missing="$$missing$$lack"; \
		else \
			echo "ok        $${entry%%:*}"; \
		fi; \
	done; \
	[ -n "$$missing" ] || exit 0; \
	echo; \
	for cmd in $$(echo "$$missing" | tr ' ' '\n' | sort -u); do \
		case "$$cmd" in \
			git)      echo "  git: https://git-scm.com/downloads" ;; \
			gh)       echo "  gh: https://cli.github.com" ;; \
			python3)  echo "  python3: https://www.python.org/downloads" ;; \
			openspec) echo "  openspec: npm install -g @fission-ai/openspec" ;; \
		esac; \
	done; \
	exit 1

.PHONY: install-skills
install-skills:
	@# A missing command only disables the skills that call it, so report and carry on.
	@$(MAKE) --no-print-directory check 2>/dev/null || true
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
