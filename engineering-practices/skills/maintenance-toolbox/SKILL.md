---
name: maintenance-toolbox
description: Detect and record a project's dead-code, unused-dependency, lint, test and coverage commands as a `## Maintenance toolbox` section in its CLAUDE.md, so deletions can be proven before they are made. Trigger on "/maintenance-toolbox", "set up the maintenance toolbox", "which dead-code tool does this repo have", or when the leave-it-smaller SessionStart hint reports the section is missing.
---

# Maintenance toolbox

The "leave the code smaller than you found it" contract asks the agent to prove code is
unused before deleting it. That proof is cheap only when the project's own tools are known:
which command lists dead code, which one lists unused dependencies, which one runs the tests.
This skill finds those tools **together with the user** and records them once, as a short
`## Maintenance toolbox` section in the project's `CLAUDE.md`, where every later session
reads them.

It is a **record, not an audit**. Do not fix any finding the tools report while running it;
that is `/codebase-maintenance`'s job.

## Steps

1. **Detect the stack.** List the manifests at the repo root and one level down:
   `pyproject.toml` / `setup.cfg` / `requirements*.txt`, `package.json` (+ lockfile, `tsconfig.json`),
   `go.mod`, `Cargo.toml`, `pom.xml` / `build.gradle(.kts)`, `Gemfile`, `*.csproj`, `composer.json`.
   A monorepo may have several; record one toolbox per stack, each with its working directory.

2. **Find what is already configured.** Read the manifest's dev dependencies and tool config
   (`[tool.*]` tables, `eslint`/`knip` config files, `Makefile`/`justfile`/`package.json` scripts,
   CI workflow steps) and confirm what is runnable (`command -v`, `npx --no-install <tool> --version`,
   `poetry run <tool> --version`). The project's existing test and lint commands always win over
   the defaults below. Candidates by stack:

   | Stack | Dead code | Unused dependencies | Unused imports/vars | Tests / coverage |
   |---|---|---|---|---|
   | Python | `vulture <pkg> --min-confidence 80` | `deptry .` | `ruff check --select F401,F841,ARG` | `pytest`, `coverage run -m pytest && coverage report` |
   | JS/TS | `npx knip` (exports, files, deps in one) | `npx knip` or `npx depcheck` | `eslint` with `no-unused-vars` | `npm test`, `npx vitest run --coverage` / `jest --coverage` |
   | Go | `staticcheck ./...` (U1000) or `golangci-lint run --enable unused` | `go mod tidy && git diff --exit-code go.mod` | `go vet ./...` | `go test ./... -cover` |
   | Rust | `cargo clippy` (`dead_code` warnings) | `cargo machete` or `cargo udeps` | `cargo clippy -- -W unused` | `cargo test`, `cargo llvm-cov` |
   | JVM | PMD `UnusedPrivateMethod/Field` rules, IntelliJ inspections | Gradle `dependency-analysis` plugin | compiler `-Xlint` | `./gradlew test` / `mvn test`, JaCoCo |
   | Shell | `shellcheck` (SC2034 unused vars) | n/a | `shellcheck` | project's test script |

3. **Propose the section and ask once.** Show the user the draft section built from what is
   present, and list the gaps (a row with no runnable tool). Ask a single question: record only
   what exists, or also add the missing tools as dev dependencies. Never install anything without
   that answer. If the user declines the whole thing, write `<!-- maintenance-toolbox: none -->`
   into `CLAUDE.md` instead, so the SessionStart hint stops.

4. **Verify each recorded command runs.** Execute every command once from the recorded working
   directory. A command that fails to start (missing binary, wrong path) is not recorded; a command
   that runs and reports findings is fine (findings are the point). Report the counts it found
   without acting on them.

5. **Write the section.** Append (or replace) a `## Maintenance toolbox` section in the project's
   `CLAUDE.md`, using this shape and nothing longer:

   ```markdown
   ## Maintenance toolbox
   <!-- maintenance-toolbox: recorded YYYY-MM-DD by /maintenance-toolbox -->
   Run before deleting anything, and again before handing back:
   - Dead code: `poetry run vulture src --min-confidence 80`
   - Unused dependencies: `poetry run deptry .`
   - Unused imports/vars: `poetry run ruff check --select F401,F841,ARG src tests`
   - Tests: `poetry run pytest`
   - Coverage: `poetry run coverage run -m pytest && poetry run coverage report`
   Not available here: (none) / <tool> — a caller grep is the proof instead.
   ```

   Keep one command per line and no explanation; the section is read by an agent at deletion
   time, not by a newcomer. If the project has no `CLAUDE.md`, create one holding only this section.

6. **Finish.** Summarise what was recorded, what is missing, and that no findings were fixed.
   Commit only if the user's workflow commits CLAUDE.md changes as a matter of course; otherwise
   leave the edit in the working tree and say so.

## Rules

- Never fix findings during this skill. Name them; `/codebase-maintenance` fixes them.
- Never add a dependency or change CI without the user's explicit yes in step 3.
- Prefer the project's own scripts (`make lint`, `npm run test`) over raw tool invocations
  when they exist; the toolbox should match how the team already runs things.
- One question to the user, in step 3. Everything else is detection and verification.
