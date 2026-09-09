# Go tooling

**Check the project first.** A `Makefile`, `.golangci.yml`, `.pre-commit-config.yaml`
or CI workflow usually records the tooling the team already chose. Prefer their
commands and their configured rule set over anything below — matching the team's gate
means your findings are ones they will act on, and your fixes pass their CI.

Probe availability before relying on a tool, and note in the audit what was
unavailable rather than silently skipping it:

```bash
command -v golangci-lint staticcheck deadcode govulncheck gocyclo 2>/dev/null
```

Install into a temp path if needed (`GOBIN=$(mktemp -d) go install ...`) rather than
mutating the user's environment or the project's `go.mod`.

## Baseline

```bash
go build ./...
go vet ./...
go test ./... 2>&1 | tail -30
gofmt -l .                                  # non-empty output = unformatted files
```

## DEAD

```bash
go install golang.org/x/tools/cmd/deadcode@latest
deadcode ./...                              # unreachable funcs from all mains+tests
deadcode -test ./...                        # include tests as entry points

staticcheck ./... | grep -E 'U1000|SA4006'  # unused code, unused writes
golangci-lint run --disable-all -E unused -E unparam -E ineffassign
```

Go-specific false positives to rule out before deleting:

- **Build tags** — `grep -rn '//go:build' .` A symbol used only under
  `//go:build linux` looks dead on a Mac. Re-check with
  `GOOS=linux GOARCH=amd64 deadcode ./...` for each platform the project targets.
- **`init()` registration** — plugins, `database/sql` drivers, `flag` definitions.
  Registered-by-side-effect code has no visible caller.
- **Interface satisfaction** — a method may exist only to satisfy an interface; check
  for `var _ Iface = (*T)(nil)` assertions.
- **`reflect` and struct tags** — a field with no code reference may be part of a JSON
  or DB contract. `grep -rn 'reflect\.' .` and read the tags.
- **Library exports** — if the module is imported by other repos, exported symbols
  with no internal caller are the product. Check whether the repo is a library before
  proposing any exported deletion.
- **`go:generate` and generated files** — fix the generator, never the output.
- **Testdata** — files under `testdata/` are ignored by the toolchain but may be read
  at runtime by tests.

## DUP

No strong native clone detector; combine:

```bash
go install github.com/mibk/dupl@latest
dupl -threshold 50 ./...

golangci-lint run --disable-all -E dupl -E goconst   # goconst finds repeated literals
```

## DEP

```bash
go mod tidy && git diff --stat go.mod go.sum         # non-empty = manifest was stale
go list -m -u all                                    # available updates
go mod graph                                         # who pulls what
govulncheck ./...                                    # known vulns, reachability-aware
go list -m -json all | grep -A2 Deprecated
```

`govulncheck` is worth more than a plain advisory scan because it reports whether the
vulnerable *symbol* is actually reachable from your code — that distinction is exactly
the "reachable path" evidence a `SEC` finding needs.

For bumps: `go get example.com/mod@v1.2.3 && go mod tidy && go test ./...`. One major
bump per commit, per the `DEP` sequencing rule.

## STYLE

```bash
gofmt -l .                                  # or gofumpt -l . if the project uses it
goimports -l .                              # import grouping
golangci-lint run                           # project's own config
golangci-lint run --fix                     # auto-fixable subset
```

If the repo has no `.golangci.yml`, run the default set and propose adding a config as
a `DOC`/`STYLE` finding rather than inventing a strict rule set and burying the user in
violations.

## SEC

```bash
golangci-lint run --disable-all -E gosec
gosec -fmt=json ./...                       # if available standalone
govulncheck ./...
```

Read every `gosec` hit before reporting it — its false-positive rate on G104 (unhandled
error) and G304 (file path from variable) is high. Confirm the untrusted input path.

Grep-level checks worth running:

```bash
grep -rn 'InsecureSkipVerify\|MinVersion' --include='*.go' .
grep -rn 'md5\.\|sha1\.\|math/rand' --include='*.go' .   # rand for tokens = finding
grep -rn 'fmt.Sprintf.*SELECT\|fmt.Sprintf.*INSERT\|+ *"WHERE' --include='*.go' .
grep -rn 'exec.Command' --include='*.go' .
```

Prefer `crypto/rand` for anything security-relevant; `math/rand` in a token generator
is a real finding even though it compiles fine.

## CORRECT

```bash
go vet ./...                                # shadowing, printf, lock copying, loopvar
staticcheck ./...                           # the SA class is genuine bug detection
go test -race ./...                         # data races — run this, it earns its time
golangci-lint run --disable-all \
  -E errcheck -E nilerr -E bodyclose -E rowserrcheck -E contextcheck -E errorlint
```

`-race` is the highest-value single command in this dimension. `errcheck` finds
swallowed errors; `bodyclose` and `rowserrcheck` find the leaks that matter in
services.

Note: since Go 1.22 the loop-variable capture bug is fixed per-iteration. Check the
`go` directive in `go.mod` before flagging `for` loop closures — on modules declaring
1.22+ it is not a finding.

## PRACTICE / CLARITY

```bash
gocyclo -over 15 .                          # cyclomatic complexity
golangci-lint run --disable-all \
  -E gocognit -E gocyclo -E funlen -E nestif -E revive -E interfacebloat
go doc ./...                                # read the exported surface as a consumer
```

Reading `go doc ./...` output is a fast way to judge whether the package boundaries
make sense — if the exported surface is incoherent, that is a `PRACTICE` finding no
linter reports.

## PERF

```bash
go test -bench=. -benchmem ./...            # existing benchmarks
go test -bench=BenchmarkX -cpuprofile=cpu.out ./pkg && go tool pprof -top cpu.out
go test -bench=BenchmarkX -memprofile=mem.out ./pkg
golangci-lint run --disable-all -E prealloc
go build -gcflags='-m' ./... 2>&1 | grep escapes   # escape analysis
```

Write and commit the benchmark before optimising — that is the measurement the `PERF`
rule requires, and it stops the next person undoing the work.

## TEST

```bash
go test ./... -coverprofile=cover.out
go tool cover -func=cover.out | sort -k3 -n         # least-covered first
go tool cover -func=cover.out | tail -1             # total
go tool cover -html=cover.out -o cover.html         # per-line, for finding branches
go test ./... -count=1                              # defeat the test cache
go test ./... -count=5                              # smoke out flakiness
```

Quality signals specific to Go:

- `grep -rn 'if err != nil' --include='*_test.go' .` — tests that check for an error
  without asserting *which* error.
- Table-driven tests missing `t.Run(tc.name, ...)` produce useless failure output.
- Missing `t.Parallel()` where safe is a speed finding, not a correctness one.
- `t.Helper()` absent in helpers makes failures point at the wrong line.
