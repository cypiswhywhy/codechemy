# The skills ship inside the plugin, so `install-plugin` installs them too. This
# only removes copies an earlier revision put in ~/.claude/skills, where they would
# now shadow the plugin's.
SKILLS_DEST := $(HOME)/.claude/skills
SKILLS_MANIFEST := $(SKILLS_DEST)/.codechemy-manifest

MARKETPLACE := codechemy
PLUGIN := engineering-practices

# What each skill and the plugin shells out to, as `name:cmd,cmd`.
PREREQS := \
	self-review:git \
	push:git,gh \
	codebase-maintenance:git,gh,python3 \
	claude-customizations:python3 \
	apply-increment:git,gh,openspec \
	apply-all-increments:git,gh,openspec \
	engineering-practices:claude,python3

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
			claude)   echo "  claude: https://claude.com/claude-code" ;; \
		esac; \
	done; \
	exit 1

.PHONY: install-plugin
install-plugin:
	@command -v claude >/dev/null 2>&1 || { echo "claude not found: https://claude.com/claude-code"; exit 1; }
	@# A missing command only disables the skills that call it, so report and carry on.
	@$(MAKE) --no-print-directory check 2>/dev/null || true
	@# Point the marketplace at this clone, so the installed plugin is the one in
	@# the working tree. Re-adding an existing name just repoints it.
	@claude plugin marketplace add "$(CURDIR)"
	@# Update an existing install, install a missing one. `update` is version-driven,
	@# so it only refreshes once plugin.json names a higher version; bump it when the
	@# plugin changes, or this target has nothing to do.
	@claude plugin update $(PLUGIN)@$(MARKETPLACE) -y 2>/dev/null \
		|| claude plugin install $(PLUGIN)@$(MARKETPLACE) -y

.PHONY: uninstall-plugin
uninstall-plugin:
	@command -v claude >/dev/null 2>&1 || { echo "claude not found: https://claude.com/claude-code"; exit 1; }
	@# Both steps fail when the plugin or marketplace is already gone, which is
	@# the state this target wants, so neither failure is an error here.
	@claude plugin uninstall $(PLUGIN)@$(MARKETPLACE) -y || true
	@claude plugin marketplace remove $(MARKETPLACE) || true

.PHONY: migrate-skills
migrate-skills:
	@if [ ! -f "$(SKILLS_MANIFEST)" ]; then \
		echo "nothing to migrate: no skills in $(SKILLS_DEST) came from this repo"; \
	else \
		while read -r name; do \
			[ -n "$$name" ] || continue; \
			rm -rf "$(SKILLS_DEST)/$$name"; \
			echo "removed   $$name (the plugin provides it now)"; \
		done < "$(SKILLS_MANIFEST)"; \
		rm -f "$(SKILLS_MANIFEST)"; \
	fi
