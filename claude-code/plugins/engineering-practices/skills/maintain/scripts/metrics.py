#!/usr/bin/env python3
"""Measure a repository before and after a maintenance run.

The point of this script is to keep the final report honest. "The codebase is in
better shape" is an assertion; "-1,847 LOC, 34 fewer lint findings, branch coverage
61% -> 78%, two dependencies removed" is a measurement. Anything the tooling could
not measure is reported as `unavailable` with a reason, so the report never quotes a
number nobody produced.

Stdlib only. Every external tool is optional and probed before use.

Requires Python 3.9 or newer; verified on 3.9 through 3.13. The `X | None`
annotations would normally need 3.10, but `from __future__ import annotations`
below defers them, so they never evaluate at runtime.

Usage:
    metrics.py snapshot [--out FILE] [--root DIR] [--skip-slow] [--quiet]
    metrics.py compare BEFORE.json AFTER.json [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Directories that are never the project's own code.
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".maintenance",
    "vendor", "node_modules", "bower_components",
    ".venv", "venv", "env", ".tox", ".nox", "__pycache__",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", ".cache",
    "dist", "build", "target", "out", "bin", "obj",
    ".next", ".nuxt", ".svelte-kit", "coverage", "htmlcov",
    "site-packages", "eggs", ".eggs",
}

# Generated artefacts: fix the generator, never the output, so don't count them.
GENERATED_PATTERNS = [
    re.compile(r"\.pb\.go$"), re.compile(r"_pb2\.py$"), re.compile(r"_pb2_grpc\.py$"),
    re.compile(r"\.gen\.go$"), re.compile(r"_generated\.go$"), re.compile(r"_gen\.go$"),
    re.compile(r"\.generated\.[a-z]+$"), re.compile(r"\.min\.(js|css)$"),
    re.compile(r"(^|/)mock_[^/]+\.go$"), re.compile(r"\.designer\.cs$"),
]

CODE_EXTENSIONS = {
    ".go": "Go", ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".jsx": "JavaScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".rb": "Ruby", ".rs": "Rust", ".c": "C", ".h": "C", ".cc": "C++",
    ".cpp": "C++", ".hpp": "C++", ".cs": "C#", ".php": "PHP", ".swift": "Swift",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".sql": "SQL", ".proto": "Protobuf",
}

DOC_EXTENSIONS = {".md", ".rst", ".adoc", ".txt"}

TEST_HINT = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*$|_test\.[a-z]+$|"
                       r"\.test\.[a-z]+$|\.spec\.[a-z]+$|(^|/)conftest\.py$")

TODO_MARKER = re.compile(rb"\b(TODO|FIXME|XXX|HACK)\b")


# --------------------------------------------------------------------------- shell

def run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    """Run a command, returning (returncode, combined output). Never raises."""
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, errors="replace",
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"__TIMEOUT__ after {timeout}s"
    except (OSError, ValueError) as exc:
        return -1, f"__ERROR__ {exc}"


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


# ----------------------------------------------------------------------- inventory

def is_generated(rel: str) -> bool:
    return any(p.search(rel) for p in GENERATED_PATTERNS)


def is_excluded(rel: str) -> bool:
    return any(part in EXCLUDED_DIRS for part in Path(rel).parts)


def list_files(root: Path) -> tuple[list[str], str]:
    """Tracked files, preferring git so untracked build output is ignored."""
    code, out = run(["git", "ls-files", "-z"], root, timeout=60)
    if code == 0 and out:
        files = [f for f in out.split("\0") if f]
        if files:
            return files, "git"

    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for name in filenames:
            files.append(str(Path(dirpath, name).relative_to(root)))
    return files, "walk"


def count_lines(path: Path) -> tuple[int, int]:
    """(physical lines, non-blank lines). Binary files count as zero."""
    try:
        data = path.read_bytes()
    except OSError:
        return 0, 0
    if b"\0" in data[:8192]:
        return 0, 0
    lines = data.splitlines()
    return len(lines), sum(1 for line in lines if line.strip())


def inventory(root: Path) -> dict:
    files, source = list_files(root)

    by_lang: dict[str, dict[str, int]] = {}
    totals = {"files": 0, "lines": 0, "code_lines": 0}
    tests = {"files": 0, "lines": 0}
    docs = {"files": 0, "lines": 0}
    todos = 0
    skipped = {"generated": 0, "excluded": 0}

    for rel in files:
        if is_excluded(rel):
            skipped["excluded"] += 1
            continue
        if is_generated(rel):
            skipped["generated"] += 1
            continue

        path = root / rel
        if not path.is_file():
            continue
        ext = path.suffix.lower()

        if ext in DOC_EXTENSIONS:
            physical, nonblank = count_lines(path)
            docs["files"] += 1
            docs["lines"] += nonblank
            continue

        lang = CODE_EXTENSIONS.get(ext)
        if lang is None:
            continue

        physical, nonblank = count_lines(path)
        bucket = by_lang.setdefault(lang, {"files": 0, "lines": 0})
        bucket["files"] += 1
        bucket["lines"] += nonblank

        totals["files"] += 1
        totals["lines"] += physical
        totals["code_lines"] += nonblank

        if TEST_HINT.search(rel):
            tests["files"] += 1
            tests["lines"] += nonblank

        try:
            todos += len(TODO_MARKER.findall(path.read_bytes()))
        except OSError:
            pass

    ranked = dict(sorted(by_lang.items(), key=lambda kv: -kv[1]["lines"]))
    primary = next(iter(ranked), None)

    return {
        "file_list_source": source,
        "primary_language": primary,
        "languages": ranked,
        "code": totals,
        "tests": tests,
        "docs": docs,
        "todo_markers": todos,
        "skipped": skipped,
        "test_to_code_ratio": (
            round(tests["lines"] / (totals["code_lines"] - tests["lines"]), 3)
            if totals["code_lines"] > tests["lines"] else None
        ),
    }


# --------------------------------------------------------------------- dependencies

def go_deps(root: Path) -> dict | None:
    mod = root / "go.mod"
    if not mod.exists():
        return None
    try:
        text = mod.read_text(errors="replace")
    except OSError:
        return None

    direct = indirect = 0
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block and line == ")":
            in_block = False
            continue
        is_req = in_block or line.startswith("require ")
        if not is_req or not line or line.startswith("//"):
            continue
        if "// indirect" in line:
            indirect += 1
        else:
            direct += 1

    result = {"direct": direct, "indirect": indirect}
    match = re.search(r"^go\s+(\S+)", text, re.M)
    if match:
        result["go_directive"] = match.group(1)
    return result


def python_deps(root: Path) -> dict | None:
    found = {}

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(errors="replace")
        except OSError:
            text = ""
        block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
        if block:
            found["pyproject_dependencies"] = len(
                [x for x in re.findall(r'"[^"]+"|\'[^\']+\'', block.group(1))]
            )
        poetry = re.search(r"\[tool\.poetry\.dependencies\](.*?)(?=^\[|\Z)",
                           text, re.S | re.M)
        if poetry:
            found["poetry_dependencies"] = len(
                [ln for ln in poetry.group(1).splitlines()
                 if re.match(r"\s*[A-Za-z0-9_.-]+\s*=", ln)
                 and not ln.strip().startswith("python")]
            )
        requires = re.search(r'requires-python\s*=\s*["\']([^"\']+)', text)
        if requires:
            found["requires_python"] = requires.group(1)

    for name in ("requirements.txt", "requirements/base.txt", "requirements-dev.txt"):
        req = root / name
        if not req.exists():
            continue
        try:
            lines = req.read_text(errors="replace").splitlines()
        except OSError:
            continue
        found[name] = len([
            ln for ln in lines
            if ln.strip() and not ln.strip().startswith(("#", "-r", "--"))
        ])

    return found or None


def dependencies(root: Path) -> dict:
    result: dict = {}
    go = go_deps(root)
    if go:
        result["go"] = go
    py = python_deps(root)
    if py:
        result["python"] = py

    node = root / "package.json"
    if node.exists():
        try:
            data = json.loads(node.read_text(errors="replace"))
            result["node"] = {
                "dependencies": len(data.get("dependencies") or {}),
                "devDependencies": len(data.get("devDependencies") or {}),
            }
        except (OSError, json.JSONDecodeError):
            pass

    return result


# ------------------------------------------------------------------- tool measures

def unavailable(reason: str) -> dict:
    return {"status": "unavailable", "reason": reason}


def measured(value, **extra) -> dict:
    return {"status": "measured", "value": value, **extra}


def untrustworthy(code: int, out: str, ok_codes: tuple[int, ...],
                  tool: str) -> dict | None:
    """Return an `unavailable` result when a tool run cannot be believed.

    A linter dying on a config error prints nothing our regex matches, so counting
    matches would yield a confident `0 findings`. Absence of parseable output means
    "we do not know", never "there is nothing there". Callers pass the exit codes
    meaning "ran to completion" -- not just 0, since for most of these tools a
    non-zero exit is the success path.
    """
    if "__TIMEOUT__" in out:
        return unavailable(f"{tool} timed out: {out.strip()}")
    if "__ERROR__" in out:
        return unavailable(f"{tool} could not be executed: {out.strip()}")
    if code not in ok_codes:
        expected = "/".join(str(c) for c in ok_codes)
        detail = " ".join(out.split())[:200] or "no output"
        return unavailable(f"{tool} exited {code}, expected {expected}: {detail}")
    return None


def reconcile(count: int, code: int, findings_code: int | None, tool: str,
              out: str) -> dict | None:
    """Catch the case where exit status and parsed output contradict each other.

    Tools that signal findings via exit code (go vet/ruff/golangci-lint 1,
    govulncheck 3) exiting that way with nothing parseable means either the tool
    failed while still exiting with that code -- `go vet` does this for build and
    module errors -- or its output format moved. Either way the zero is fiction.
    Pass findings_code=None for tools that always exit 0, like `gofmt -l`.
    """
    if findings_code is not None and code == findings_code and count == 0:
        detail = " ".join(out.split())[:200] or "no output"
        return unavailable(
            f"{tool} exited {code} (which signals findings) but none were "
            f"parseable -- likely a build error or a changed output format: "
            f"{detail}")
    return None


def count_lint(root: Path, lang: str | None) -> dict:
    """Lint finding count. Uses the project's own config, whatever that is."""
    if lang == "Go":
        # Exits 0 clean, 1 with findings; anything else means it did not run.
        # Can also be on PATH but unrunnable, so fall through to `go vet`.
        if have("golangci-lint"):
            code, out = run(["golangci-lint", "run", "--out-format", "line-number"],
                            root, timeout=300)
            hits = [ln for ln in out.splitlines() if re.match(r"^\S+\.go:\d+:", ln)]
            if (untrustworthy(code, out, (0, 1), "golangci-lint") is None
                    and reconcile(len(hits), code, 1, "golangci-lint", out) is None):
                return measured(len(hits), tool="golangci-lint")
        if have("go"):
            # Exits 1 for build/module errors too, so reconcile() catches the
            # case where it exited 1 but printed nothing we recognise.
            code, out = run(["go", "vet", "./..."], root, timeout=180)
            problem = untrustworthy(code, out, (0, 1), "go vet")
            if problem:
                return problem
            hits = [ln for ln in out.splitlines() if re.search(r"\.go:\d+:", ln)]
            problem = reconcile(len(hits), code, 1, "go vet", out)
            if problem:
                return problem
            return measured(len(hits), tool="go vet")
        return unavailable("neither golangci-lint nor go usable on PATH")

    if lang == "Python":
        # ruff exits 0 clean, 1 with violations, 2 on error.
        if have("ruff"):
            code, out = run(["ruff", "check", "--output-format", "concise", "."],
                            root, timeout=180)
            problem = untrustworthy(code, out, (0, 1), "ruff check")
            if problem:
                return problem
            hits = [ln for ln in out.splitlines() if re.match(r"^\S+:\d+:\d+:", ln)]
            problem = reconcile(len(hits), code, 1, "ruff check", out)
            if problem:
                return problem
            return measured(len(hits), tool="ruff")
        return unavailable("ruff not on PATH")

    return unavailable(f"no lint measure configured for {lang or 'unknown language'}")


def count_format_drift(root: Path, lang: str | None) -> dict:
    """Files the project's formatter would change."""
    if lang == "Go":
        # gofmt/gofumpt -l exits 0 even when it lists files; non-zero means it
        # could not parse the tree, in which case the empty list is meaningless.
        tool = "gofumpt" if have("gofumpt") else ("gofmt" if have("gofmt") else None)
        if not tool:
            return unavailable("no gofmt/gofumpt on PATH")
        # Exits 0 even when listing files, so no findings code to reconcile.
        code, out = run([tool, "-l", "."], root, timeout=120)
        problem = untrustworthy(code, out, (0,), tool)
        if problem:
            return problem
        files = [ln for ln in out.splitlines() if ln.strip().endswith(".go")]
        return measured(len(files), tool=tool)

    if lang == "Python":
        # Both exit 1 when files would be reformatted: ruff 2 on error, black 123.
        if have("ruff"):
            code, out = run(["ruff", "format", "--check", "."], root, timeout=180)
            problem = untrustworthy(code, out, (0, 1), "ruff format")
            if problem:
                return problem
            files = [ln for ln in out.splitlines() if ln.startswith("Would reformat")]
            problem = reconcile(len(files), code, 1, "ruff format", out)
            if problem:
                return problem
            return measured(len(files), tool="ruff format")
        if have("black"):
            code, out = run(["black", "--check", "."], root, timeout=180)
            problem = untrustworthy(code, out, (0, 1), "black")
            if problem:
                return problem
            files = [ln for ln in out.splitlines() if ln.startswith("would reformat")]
            problem = reconcile(len(files), code, 1, "black", out)
            if problem:
                return problem
            return measured(len(files), tool="black")
        return unavailable("neither ruff nor black on PATH")

    return unavailable(f"no format measure configured for {lang or 'unknown language'}")


def count_vulns(root: Path, lang: str | None) -> dict:
    """Known-vulnerability count.

    A false zero is the worst output here: it reads as "audited, nothing found".
    """
    if lang == "Go" and have("govulncheck"):
        # govulncheck exits 0 when clean and 3 when vulnerabilities are found.
        code, out = run(["govulncheck", "./..."], root, timeout=300)
        problem = untrustworthy(code, out, (0, 3), "govulncheck")
        if problem:
            return problem
        found = len(re.findall(r"^Vulnerability #\d+", out, re.M))
        problem = reconcile(found, code, 3, "govulncheck", out)
        if problem:
            return problem
        return measured(found, tool="govulncheck")
    if lang == "Python" and have("pip-audit"):
        # pip-audit exits 0 when clean and 1 when vulnerabilities are found.
        code, out = run(["pip-audit", "--format", "json"], root, timeout=300)
        problem = untrustworthy(code, out, (0, 1), "pip-audit")
        if problem:
            return problem
        try:
            data = json.loads(out)
            deps = data.get("dependencies", data) if isinstance(data, dict) else data
            total = sum(len(d.get("vulns", [])) for d in deps
                        if isinstance(d, dict))
            return measured(total, tool="pip-audit")
        except (json.JSONDecodeError, AttributeError, TypeError):
            return unavailable("pip-audit output not parseable")
    return unavailable("no vulnerability scanner available for this stack")


def measure_coverage(root: Path, lang: str | None) -> dict:
    """Runs the test suite. Slow by nature -- gated behind --skip-slow."""
    if lang == "Go" and have("go"):
        # Coverage still prints on a failing run, so flag it: a number measured
        # against red tests should not read as clean.
        code, out = run(["go", "test", "-cover", "./..."], root, timeout=900)
        problem = untrustworthy(code, out, (0, 1), "go test -cover")
        if problem:
            return problem
        pcts = [float(m) for m in re.findall(r"coverage: ([\d.]+)% of statements", out)]
        if not pcts:
            return unavailable("no coverage reported (tests may not exist or failed)")
        # Untested packages print "[no test files]" and drop out, so this reads
        # high on sparse repos -- `packages_reporting` is the check on that.
        return measured(round(sum(pcts) / len(pcts), 2),
                        unit="percent statements (mean over reporting packages)",
                        tool="go test -cover", packages_reporting=len(pcts),
                        suite_passed=(code == 0))

    if lang == "Python" and have("pytest"):
        # 0 = all passed, 1 = some test failed; 2-5 are usage/collection errors.
        code, out = run(["pytest", "--cov", "--cov-branch",
                         "--cov-report=term", "-q"], root, timeout=900)
        problem = untrustworthy(code, out, (0, 1), "pytest --cov")
        if problem:
            return problem
        match = re.search(r"^TOTAL\s+.*?(\d+)%\s*$", out, re.M)
        if match:
            return measured(float(match.group(1)),
                            unit="percent branch", tool="pytest --cov-branch",
                            suite_passed=(code == 0))
        return unavailable("pytest-cov produced no TOTAL line "
                           "(plugin missing, or tests failed)")

    return unavailable("no coverage tool available for this stack")


def git_facts(root: Path) -> dict:
    facts: dict = {}
    for key, cmd in (
        ("branch", ["git", "branch", "--show-current"]),
        ("head", ["git", "rev-parse", "--short", "HEAD"]),
    ):
        code, out = run(cmd, root, timeout=30)
        if code == 0:
            facts[key] = out.strip()
    code, out = run(["git", "status", "--porcelain"], root, timeout=60)
    if code == 0:
        facts["dirty_files"] = len([ln for ln in out.splitlines() if ln.strip()])
    return facts


# ------------------------------------------------------------------------ snapshot

def snapshot(root: Path, skip_slow: bool) -> dict:
    inv = inventory(root)
    lang = inv["primary_language"]
    return {
        "schema": 1,
        "taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": str(root.resolve()),
        "git": git_facts(root),
        "inventory": inv,
        "dependencies": dependencies(root),
        "quality": {
            "lint_findings": count_lint(root, lang),
            "unformatted_files": count_format_drift(root, lang),
            "known_vulnerabilities": count_vulns(root, lang),
            "coverage": (unavailable("skipped via --skip-slow") if skip_slow
                         else measure_coverage(root, lang)),
        },
    }


# ------------------------------------------------------------------------- compare

def delta(before, after) -> str:
    if before is None or after is None:
        return "n/a"
    diff = after - before
    if isinstance(diff, float):
        diff = round(diff, 2)
    return f"{diff:+g}"


def pick(snap: dict, *path):
    node = snap
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def quality_value(snap: dict, key: str):
    node = pick(snap, "quality", key)
    if isinstance(node, dict) and node.get("status") == "measured":
        return node.get("value")
    return None


def quality_note(snap: dict, key: str) -> str | None:
    node = pick(snap, "quality", key)
    if isinstance(node, dict) and node.get("status") == "unavailable":
        return node.get("reason")
    return None


def total_deps(snap: dict) -> int | None:
    deps = snap.get("dependencies") or {}
    total = 0
    seen = False
    go = deps.get("go")
    if isinstance(go, dict):
        total += go.get("direct", 0)
        seen = True
    py = deps.get("python")
    if isinstance(py, dict):
        for key in ("pyproject_dependencies", "poetry_dependencies",
                    "requirements.txt"):
            if key in py:
                total += py[key]
                seen = True
                break
    node = deps.get("node")
    if isinstance(node, dict):
        total += node.get("dependencies", 0)
        seen = True
    return total if seen else None


def compare(before: dict, after: dict) -> dict:
    rows = [
        ("Code lines (non-blank)",
         pick(before, "inventory", "code", "code_lines"),
         pick(after, "inventory", "code", "code_lines")),
        ("Code files",
         pick(before, "inventory", "code", "files"),
         pick(after, "inventory", "code", "files")),
        ("Test lines",
         pick(before, "inventory", "tests", "lines"),
         pick(after, "inventory", "tests", "lines")),
        ("Doc lines",
         pick(before, "inventory", "docs", "lines"),
         pick(after, "inventory", "docs", "lines")),
        ("TODO/FIXME markers",
         pick(before, "inventory", "todo_markers"),
         pick(after, "inventory", "todo_markers")),
        ("Direct dependencies", total_deps(before), total_deps(after)),
        ("Lint findings",
         quality_value(before, "lint_findings"),
         quality_value(after, "lint_findings")),
        ("Unformatted files",
         quality_value(before, "unformatted_files"),
         quality_value(after, "unformatted_files")),
        ("Known vulnerabilities",
         quality_value(before, "known_vulnerabilities"),
         quality_value(after, "known_vulnerabilities")),
        ("Coverage %",
         quality_value(before, "coverage"),
         quality_value(after, "coverage")),
    ]

    notes = []
    for key, label in (
        ("lint_findings", "Lint findings"),
        ("unformatted_files", "Unformatted files"),
        ("known_vulnerabilities", "Known vulnerabilities"),
        ("coverage", "Coverage %"),
    ):
        for when, snap in (("before", before), ("after", after)):
            reason = quality_note(snap, key)
            if reason:
                notes.append(f"{label} not measured ({when}): {reason}")

    return {
        "rows": [
            {"metric": m, "before": b, "after": a, "delta": delta(b, a)}
            for m, b, a in rows
        ],
        "unavailable": notes,
    }


def render(result: dict) -> str:
    rows = result["rows"]
    width = max(len(r["metric"]) for r in rows)
    lines = [
        f"{'Metric'.ljust(width)}  {'Before':>10}  {'After':>10}  {'Delta':>9}",
        f"{'-' * width}  {'-' * 10}  {'-' * 10}  {'-' * 9}",
    ]
    for row in rows:
        before = "-" if row["before"] is None else f"{row['before']:g}"
        after = "-" if row["after"] is None else f"{row['after']:g}"
        lines.append(f"{row['metric'].ljust(width)}  {before:>10}  "
                     f"{after:>10}  {row['delta']:>9}")

    if result["unavailable"]:
        lines.append("")
        lines.append("Not measured — do not quote these as numbers:")
        lines.extend(f"  - {note}" for note in result["unavailable"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="measure the repository now")
    snap.add_argument("--root", default=".", help="repository root (default: cwd)")
    snap.add_argument("--out", help="write JSON here (default: stdout)")
    snap.add_argument("--skip-slow", action="store_true",
                      help="skip anything that runs the test suite")
    snap.add_argument("--quiet", action="store_true", help="suppress the summary")

    cmp_ = sub.add_parser("compare", help="diff two snapshots")
    cmp_.add_argument("before")
    cmp_.add_argument("after")
    cmp_.add_argument("--json", action="store_true", help="emit JSON not a table")

    args = parser.parse_args(argv)

    if args.command == "snapshot":
        root = Path(args.root).expanduser()
        if not root.is_dir():
            print(f"error: {root} is not a directory", file=sys.stderr)
            return 2

        data = snapshot(root, args.skip_slow)
        payload = json.dumps(data, indent=2, sort_keys=False)

        if args.out:
            out = Path(args.out).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload + "\n")
            if not args.quiet:
                inv = data["inventory"]
                print(f"Wrote {out}")
                print(f"  primary language : {inv['primary_language'] or 'unknown'}")
                print(f"  code             : {inv['code']['code_lines']:,} lines "
                      f"in {inv['code']['files']:,} files")
                print(f"  tests            : {inv['tests']['lines']:,} lines "
                      f"in {inv['tests']['files']:,} files")
                for key, node in data["quality"].items():
                    if node.get("status") == "measured":
                        print(f"  {key:<17}: {node['value']} "
                              f"({node.get('tool', 'n/a')})")
                    else:
                        print(f"  {key:<17}: unavailable — {node['reason']}")
        else:
            print(payload)
        return 0

    try:
        before = json.loads(Path(args.before).read_text())
        after = json.loads(Path(args.after).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error reading snapshots: {exc}", file=sys.stderr)
        return 2

    result = compare(before, after)
    print(json.dumps(result, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
