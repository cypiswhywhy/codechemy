#!/usr/bin/env python3
"""leave-it-smaller: Claude Code hooks for the "leave the code smaller than you found it" contract.

    python3 leave_it_smaller.py stop            # Stop hook
    python3 leave_it_smaller.py session-start   # SessionStart hook

Stop: measures what this session changed (the branch versus its base, plus the working tree,
less what was already pending at session start) and blocks the stop when it fails one of three
checks - the session only added lines, it edited source without touching a test in a repository
that has tests, or a source file grew mostly by comments and docstrings. The nudge is bounded:
never while the agent is already continuing because of a stop hook, never twice for the same
diff, each check at most once per session, and at most LEAVE_IT_SMALLER_MAX_NUDGES blocked stops
in all. Otherwise the shape is shown to the user as a one-line system message.

SessionStart: records what is already pending, so a session is asked only about its own
changes, and points the agent at /maintenance-toolbox when the repository's CLAUDE.md has no
`## Maintenance toolbox` section (the place the dead-code / lint / test commands are recorded).

Both are silent in a project whose CLAUDE.md carries practices.OPT_OUT.

Stdlib only. Never fails the session: any unexpected error is logged and exits 0.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import tokenize
from datetime import datetime
from pathlib import Path, PurePosixPath

from practices import OPT_OUT, project_instructions, read_payload


def _env_number(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


# A change that gained at least MIN_ADDED lines while losing fewer than MAX_RATIO of
# that count reads as "add-only", whether the lines landed in existing files or new ones.
MIN_ADDED = int(_env_number("LEAVE_IT_SMALLER_MIN_ADDED", 40))
MAX_RATIO = _env_number("LEAVE_IT_SMALLER_MAX_RATIO", 0.10)
# Total changed lines from which the reported shape carries "large change".
LARGE = int(_env_number("LEAVE_IT_SMALLER_LARGE", 400))
# Upper bound on blocked stops per session.
MAX_NUDGES = int(_env_number("LEAVE_IT_SMALLER_MAX_NUDGES", 2))
# A source file that grew by at least PROSE_MIN_ADDED lines, of which PROSE_SHARE or more are
# comments or docstrings, and by PROSE_GAP more than the file's own density, reads as
# "prose-heavy": the change did not match the density of the file it is in.
PROSE_MIN_ADDED = 20
PROSE_SHARE = _env_number("LEAVE_IT_SMALLER_PROSE_SHARE", 0.40)
PROSE_GAP = 0.15

CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
STATE_DIR = CONFIG_DIR / "leave-it-smaller" / "sessions"
LOG_FILE = CONFIG_DIR / "leave-it-smaller" / "hook.log"
STATE_TTL_SECONDS = 7 * 24 * 3600

TOOLBOX_HEADING = "## Maintenance toolbox"
TOOLBOX_OPT_OUT = "maintenance-toolbox: none"

DEFAULT_BRANCH_CANDIDATES = ("origin/HEAD", "origin/main", "origin/master", "main", "master")
MAX_UNTRACKED_FILES = 200
MAX_TEXT_BYTES = 1_000_000

# Directories and filename shapes that mean "this file is a test", across the common
# conventions. Used both to spot a repository that has a harness at all and to tell a
# behaviour change from the test that should have come with it.
TEST_DIR_NAMES = {"test", "tests", "spec", "specs", "__tests__", "testdata"}
TEST_NAME_PREFIXES = ("test_", "spec_")
TEST_STEM_SUFFIXES = ("_test", "_spec", ".test", ".spec", "Test", "Tests", "Spec", "Specs")
# Extensions that hold no behaviour, so a change confined to them needs no test.
NON_SOURCE_SUFFIXES = {
    "", ".md", ".markdown", ".rst", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".lock", ".csv", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".gitignore", ".editorconfig", ".env",
}
# Line-comment prefixes per language, for the prose count outside Python (where the tokenizer
# and the AST count comments and docstrings exactly).
COMMENT_PREFIXES = {
    ".js": ("//", "/*", "*"), ".jsx": ("//", "/*", "*"), ".ts": ("//", "/*", "*"),
    ".tsx": ("//", "/*", "*"), ".go": ("//", "/*", "*"), ".rs": ("//", "/*", "*"),
    ".java": ("//", "/*", "*"), ".kt": ("//", "/*", "*"), ".c": ("//", "/*", "*"),
    ".h": ("//", "/*", "*"), ".cpp": ("//", "/*", "*"), ".cs": ("//", "/*", "*"),
    ".swift": ("//", "/*", "*"), ".php": ("//", "/*", "*", "#"), ".rb": ("#",),
    ".sh": ("#",), ".bash": ("#",), ".zsh": ("#",), ".pl": ("#",), ".r": ("#",),
}
# A background command or agent announces itself at the start of its tool result, and is finished
# once a task notification names its tool use or a TaskStop result names its task.
BACKGROUND_LAUNCH_RE = re.compile(
    r"Command running in background with ID: (\w+)|Async agent launched successfully\..*?agentId: (\w+)",
    re.S,
)
TASK_DONE_RE = re.compile(r"<tool-use-id>([^<]+)</tool-use-id>")
TASK_STOPPED_RE = re.compile(r"stopped task: (\w+)")
# A task can end without its notification reaching the transcript; past this age it no longer
# holds the checks back. The longest real wait seen at a stop was 12 minutes.
BACKGROUND_STALE_SECONDS = 3600
# A transcript grows for the whole session; only its tail is read.
MAX_TRANSCRIPT_TAIL_BYTES = 256_000

ADD_ONLY_HEADER = (
    "This session added +{added} and removed only -{deleted}, across {existing_files} existing "
    "file(s) and {new_files} new one(s). Before you finish, make one pass over what you wrote:\n"
)
ADD_ONLY_MESSAGE = ADD_ONLY_HEADER + (
    "1. Does any of it duplicate something the repository already has? Grep for the concept "
    "rather than the name; where a second caller now needs what a first one had, generalise "
    "the existing code and use it in both ('Reuse before adding').\n"
    "2. Did a new path supersede an old one that is still in the tree? Delete the old one.\n"
    "3. Is there dead code, an unused import or parameter, defensive code the task did not "
    "need, or a comment or docstring that only restates the code, in what you touched?\n"
    "Prove each removal first (the project's Maintenance toolbox, then a caller grep). If "
    "nothing can go, say so in one line."
)
# A change confined to docs, specs and config has no dead code to look for.
DOCS_ADD_ONLY_MESSAGE = ADD_ONLY_HEADER + (
    "1. Does any of it repeat something the repository already has? Grep for the concept "
    "rather than the name, and point to the one place that says it instead of saying it again.\n"
    "2. Does it replace text still in the tree, such as an older section, page, spec or task? "
    "Delete the old one.\n"
    "Grep for what links to anything you remove. If nothing can go, say so in one line."
)
TESTS_MESSAGE = (
    "This change edits {source_files} source file(s) and no test changed with it, in a "
    "repository that has a test suite. Before you finish: name the behaviour this changed and "
    "the test that now covers it. If you wrote the code first, add the test now, and check it "
    "fails against the old behaviour before you keep it - a test that cannot fail asserts "
    "nothing. If the change really alters no behaviour (a rename, an extraction, config, "
    "docs), say which in your summary, with the test command you ran and its result."
)
PROSE_MESSAGE = (
    "These files grew mostly by comments and docstrings, well past the density they had:\n"
    "{files}\n"
    "A comment says why, never what, and a docstring is one line stating the contract. Before "
    "you finish, go through what you added: delete every comment that narrates the change or "
    "the review that shaped it, restates the line under it, or explains a line you could "
    "rename or split instead; cut each docstring to the contract and the surprise; keep only "
    "the reasons that live outside the code. Say what you removed, with the diff shape."
)
TOOLBOX_HINT = (
    "leave-it-smaller: this repository's CLAUDE.md has no `## Maintenance toolbox` section, so "
    "the dead-code, lint and test commands that deletions must be proven with are not recorded "
    "here. At the user's first substantive coding request, offer once to run "
    "/maintenance-toolbox (it detects them together with the user and writes the section). Do "
    "not run it unasked. If the user declines, add `<!-- maintenance-toolbox: none -->` to the "
    "repository's CLAUDE.md so this hint stops."
)


class GitError(Exception):
    pass


# ----- git -------------------------------------------------------------------


def git(cwd: str | Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20, check=False
    )
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def ref_exists(cwd: str | Path, ref: str) -> bool:
    try:
        git(cwd, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except GitError:
        return False
    return True


def merge_base(cwd: str | Path, a: str, b: str) -> str | None:
    try:
        return git(cwd, "merge-base", a, b).strip() or None
    except GitError:
        return None


def base_ref(root: str) -> str | None:
    """The commit (a full hash) the change is measured against; None with no commits yet.

    On a feature branch that is the merge-base with the default branch, so the whole
    branch counts (the PR shape). On the default branch it is the merge-base with the
    upstream when one exists (unpushed work), else HEAD (uncommitted work).
    """
    if not ref_exists(root, "HEAD"):
        return None
    head = git(root, "rev-parse", "HEAD").strip()
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    default = next((c for c in DEFAULT_BRANCH_CANDIDATES if ref_exists(root, c)), None)
    if default == "origin/HEAD":
        default = git(root, "rev-parse", "--abbrev-ref", "origin/HEAD").strip()
    default_short = default.split("/", 1)[1] if default and default.startswith("origin/") else default
    if branch != "HEAD" and default and default_short != branch:
        return merge_base(root, "HEAD", default) or head
    if ref_exists(root, "@{upstream}"):
        return merge_base(root, "HEAD", "@{upstream}") or head
    return head


def rename_target(numstat_path: str) -> str:
    """`git diff --numstat -M` renders renames as `old => new` or `dir/{old => new}/rest`."""
    if " => " not in numstat_path:
        return numstat_path
    if "{" in numstat_path and "}" in numstat_path:
        prefix, rest = numstat_path.split("{", 1)
        middle, suffix = rest.split("}", 1)
        return prefix + middle.split(" => ", 1)[1] + suffix
    return numstat_path.split(" => ", 1)[1]


def is_test_path(path: str) -> bool:
    """Whether a repository-relative path is a test, across the common conventions."""
    parts = PurePosixPath(path).parts
    if any(part in TEST_DIR_NAMES for part in parts[:-1]):
        return True
    name = PurePosixPath(path).name
    stem = name[: name.rindex(".")] if "." in name[1:] else name
    return name.startswith(TEST_NAME_PREFIXES) or stem.endswith(TEST_STEM_SUFFIXES)


def holds_code(path: str) -> bool:
    """Whether the path is code (a test included), rather than docs, config or data."""
    name = PurePosixPath(path).name
    suffix = name[name.rindex(".") :] if "." in name[1:] else ""
    return suffix not in NON_SOURCE_SUFFIXES


def is_source_path(path: str) -> bool:
    """Whether a change to this path can alter behaviour, so a test should move with it."""
    return holds_code(path) and not is_test_path(path)


def prose_lines(path: str, text: str) -> int:
    """Lines of comments and docstrings in ``text``; 0 for a language this does not read."""
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".py":
        found: set[int] = set()
        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                if tok.type == tokenize.COMMENT:
                    found.add(tok.start[0])
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = node.body[0] if node.body else None
                    if (
                        isinstance(doc, ast.Expr)
                        and isinstance(doc.value, ast.Constant)
                        and isinstance(doc.value.value, str)
                    ):
                        found.update(range(doc.lineno, (doc.end_lineno or doc.lineno) + 1))
        except (SyntaxError, ValueError, tokenize.TokenError):
            return sum(1 for line in text.splitlines() if line.lstrip().startswith("#"))
        return len(found)
    prefixes = COMMENT_PREFIXES.get(suffix)
    if not prefixes:
        return 0
    return sum(1 for line in text.splitlines() if line.lstrip().startswith(prefixes))


def is_prose_measured(path: str) -> bool:
    return is_source_path(path) and PurePosixPath(path).suffix.lower() in {".py", *COMMENT_PREFIXES}


def file_counts(root: str, path: str) -> list[int] | None:
    """[lines, prose lines] of the working copy, for a file the prose check reads; else None."""
    if not is_prose_measured(path):
        return None
    try:
        text = (Path(root) / path).read_text(errors="replace")
    except OSError:
        return None
    return [text.count("\n"), prose_lines(path, text)]


def prose_heavy_files(root: str, base: str | None, paths: list[str], baseline: dict) -> list[str]:
    """One line per source file whose growth was mostly comments and docstrings.

    A file counts when it grew by at least PROSE_MIN_ADDED lines, at least PROSE_SHARE of that
    growth is prose, and that share exceeds the file's own density before the change by
    PROSE_GAP - the practice is to match the density of the file you are in, so a file that
    was already half prose is not asked to change. "Before" is the file at session start when
    the baseline recorded it, else its version at ``base``.
    """
    rows = []
    for path in paths:
        after = file_counts(root, path)
        if after is None:
            continue
        before = (baseline.get(path) or [0, 0, None, None])[2:]
        if before[0] is None:
            text = ""
            if base is not None:
                try:
                    text = git(root, "show", f"{base}:{path}")
                except GitError:
                    pass
            before = [text.count("\n"), prose_lines(path, text)]
        before_lines, before_prose = before
        grown = after[0] - before_lines
        if grown < PROSE_MIN_ADDED:
            continue
        prose_grown = after[1] - before_prose
        share = prose_grown / grown
        density = before_prose / before_lines if before_lines else 0.0
        if share >= PROSE_SHARE and share >= density + PROSE_GAP:
            rows.append(
                f"- {path}: +{grown} lines, {prose_grown} of them comments or docstrings "
                f"({share:.0%}); the file was {density:.0%} before"
            )
    return rows


def repo_has_tests(root: str) -> bool:
    """Whether the repository has a test harness at all; without one there is nothing to ask for."""
    try:
        tracked = git(root, "ls-files").splitlines()
    except (GitError, OSError):
        return False
    return any(is_test_path(path) for path in tracked)


def count_lines(path: Path) -> int | None:
    """Line count of a text file, None for binaries and anything oversized."""
    try:
        if not path.is_file() or path.stat().st_size > MAX_TEXT_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


Row = tuple[str, int, int, bool]  # (path, added, deleted, is_new)


def pending_change(cwd: str) -> tuple[str, str | None, list[Row]] | None:
    """(repository root, base commit, per-file rows) of the pending change; None outside a repository."""
    try:
        root = git(cwd, "rev-parse", "--show-toplevel").strip()
    except (GitError, OSError):
        return None
    rows: list[Row] = []
    base = base_ref(root)
    if base is not None:
        status: dict[str, str] = {}
        for line in git(root, "diff", "--name-status", "-M", base).splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                status[parts[-1]] = parts[0][0]
        for line in git(root, "diff", "--numstat", "-M", base).splitlines():
            added, deleted, path = line.split("\t", 2)
            if added == "-":  # binary
                continue
            path = rename_target(path)
            rows.append((path, int(added), int(deleted), status.get(path) == "A"))
    untracked = git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    for path in untracked[:MAX_UNTRACKED_FILES]:
        lines = count_lines(Path(root) / path)
        if lines is not None:
            rows.append((path, lines, 0, True))
    return root, base, rows


def baseline_of(root: str, rows: list[Row]) -> dict:
    """What was already pending, per path: [added, deleted, lines, prose lines]."""
    return {
        path: [added, deleted, *(file_counts(root, path) or [None, None])]
        for path, added, deleted, _ in rows
    }


def session_rows(rows: list[Row], baseline: dict) -> list[Row]:
    """The rows less what was pending at session start, per file.

    Measured per file as the change in its counts, so lines a session adds and removes within
    one file net out. Undoing earlier work counts as removal.
    """
    out = []
    for path, added, deleted, is_new in rows:
        start_added, start_deleted = (baseline.get(path) or [0, 0])[:2]
        grew = max(0, added - start_added) + max(0, start_deleted - deleted)
        shrank = max(0, deleted - start_deleted) + max(0, start_added - added)
        if grew or shrank:
            out.append((path, grew, shrank, is_new))
    pending = {row[0] for row in rows}
    out += [(path, start[1], start[0], False) for path, start in baseline.items() if path not in pending]
    return out


def diff_shape(root: str, base: str | None, rows: list[Row], baseline: dict) -> dict:
    existing = [r for r in rows if not r[3]]
    prose_heavy = prose_heavy_files(
        root, base, [r[0] for r in rows if r[1] >= PROSE_MIN_ADDED], baseline
    )
    changed_source = [r[0] for r in rows if is_source_path(r[0])]
    changed_tests = [r[0] for r in rows if is_test_path(r[0])]
    fingerprint = hashlib.sha1(
        "\n".join(f"{p}\t{a}\t{d}" for p, a, d, _ in sorted(rows)).encode()
    ).hexdigest()
    return {
        "files": len(rows),
        "added": sum(r[1] for r in rows),
        "deleted": sum(r[2] for r in rows),
        "existing_files": len(existing),
        "existing_added": sum(r[1] for r in existing),
        "existing_deleted": sum(r[2] for r in existing),
        "new_files": len(rows) - len(existing),
        "prose_heavy": prose_heavy,
        "fingerprint": fingerprint,
        "root": root,
        "source_files": len(changed_source),
        "test_files": len(changed_tests),
        "code_files": sum(1 for r in rows if holds_code(r[0])),
    }


# ----- assessment ------------------------------------------------------------


def transcript_tail(transcript_path: str | None) -> list[dict]:
    """The entries at the end of the session transcript; [] when it is absent or unreadable."""
    if not transcript_path:
        return []
    try:
        with open(transcript_path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - MAX_TRANSCRIPT_TAIL_BYTES))
            raw = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    entries = []
    for line in raw.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def result_text(content: object) -> str:
    """A tool result's text: the string itself, or its first text block."""
    if isinstance(content, str):
        return content
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("type") == "text":
            return str(block.get("text", ""))
    return ""


def entry_time(entry: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(entry["timestamp"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None


def background_pending(transcript_path: str | None) -> bool:
    """Whether a background command or agent started in the transcript's tail has not finished.

    The stop is then a pause, not the hand-back. A transcript in an unfamiliar format reads as
    nothing pending, so the checks run as they would without this.
    """
    pending: dict[str, tuple[str, datetime | None]] = {}  # tool use id -> (task id, launched at)
    latest = None
    for entry in transcript_tail(transcript_path):
        latest = entry_time(entry) or latest
        if entry.get("type") != "user":
            continue
        content = (entry.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                launched = BACKGROUND_LAUNCH_RE.match(result_text(block.get("content")))
                if launched:
                    pending[str(block.get("tool_use_id"))] = (launched[1] or launched[2], entry_time(entry))
        text = content if isinstance(content, str) else json.dumps(content)
        for tool_use_id in TASK_DONE_RE.findall(text):
            pending.pop(tool_use_id, None)
        stopped = set(TASK_STOPPED_RE.findall(text))
        pending = {use: task for use, task in pending.items() if task[0] not in stopped}
    return any(
        not (at and latest and (latest - at).total_seconds() > BACKGROUND_STALE_SECONDS)
        for _, at in pending.values()
    )


def assess(shape: dict) -> tuple[bool, bool]:
    """(the change only added, the change is already large)."""
    add_only = (
        shape["added"] >= MIN_ADDED and shape["deleted"] < MAX_RATIO * shape["added"]
    )
    large = shape["added"] + shape["deleted"] >= LARGE
    return add_only, large


def summary_line(shape: dict) -> str:
    return (
        "leave-it-smaller: +{added} / -{deleted} across {files} file(s) "
        "({existing_files} existing: +{existing_added} / -{existing_deleted}; "
        "{new_files} new)"
    ).format(**shape)


# ----- per-session state -----------------------------------------------------


def session_of(payload: dict) -> str:
    return str(payload.get("session_id") or "unknown")


def state_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id) or "unknown"
    return STATE_DIR / f"{safe}.json"


def load_state(session_id: str) -> dict:
    try:
        return json.loads(state_path(session_id).read_text())
    except (OSError, ValueError):
        return {}


def save_state(session_id: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path(session_id).write_text(json.dumps(state))
    cutoff = time.time() - STATE_TTL_SECONDS
    for stale in STATE_DIR.glob("*.json"):
        try:
            if stale.stat().st_mtime < cutoff:
                stale.unlink()
        except OSError:
            pass


# ----- hooks -----------------------------------------------------------------


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")


def run_stop(payload: dict) -> None:
    if background_pending(payload.get("transcript_path")):
        return
    change = pending_change(payload.get("cwd") or os.getcwd())
    if change is None:
        return
    root, base, rows = change
    session_id = session_of(payload)
    state = load_state(session_id)
    if "baseline" not in state:
        # No SessionStart for this session, e.g. the plugin arrived mid-session: it all counts.
        state.update(base=base, baseline={})
    elif state.get("base") != base:
        # A push, pull or branch switch moved the base, so the old counts no longer line up.
        state.update(base=base, baseline=baseline_of(root, rows))
        save_state(session_id, state)
        return
    shape = diff_shape(root, base, session_rows(rows, state["baseline"]), state["baseline"])
    if shape["files"] == 0:
        save_state(session_id, state)
        return
    changed = state.get("fingerprint") != shape["fingerprint"]
    add_only, large = assess(shape)
    summary = summary_line(shape)

    can_nudge = (
        changed
        and not payload.get("stop_hook_active")
        and state.get("nudges", 0) < MAX_NUDGES
    )
    reasons = []
    if can_nudge and add_only and not state.get("add_only_nudged"):
        message = ADD_ONLY_MESSAGE if shape["code_files"] else DOCS_ADD_ONLY_MESSAGE
        reasons.append(message.format(**shape))
        state["add_only_nudged"] = True
    if (
        can_nudge
        and not state.get("tests_nudged")
        and shape["source_files"]
        and not shape["test_files"]
        and repo_has_tests(shape["root"])
    ):
        reasons.append(TESTS_MESSAGE.format(**shape))
        state["tests_nudged"] = True
    if can_nudge and not state.get("prose_nudged") and shape["prose_heavy"]:
        reasons.append(PROSE_MESSAGE.format(files="\n".join(shape["prose_heavy"][:5])))
        state["prose_nudged"] = True

    state["fingerprint"] = shape["fingerprint"]
    if reasons:
        state["nudges"] = state.get("nudges", 0) + 1
        save_state(session_id, state)
        emit({"decision": "block", "reason": summary + "\n\n" + "\n\n".join(reasons)})
        return
    save_state(session_id, state)
    if changed:
        flags = [f for f, on in (("add-only", add_only), ("large change", large)) if on]
        emit({"systemMessage": summary + (f" - {', '.join(flags)}" if flags else "")})


def run_session_start(payload: dict) -> None:
    change = pending_change(payload.get("cwd") or os.getcwd())
    if change is None:
        return
    root, base, rows = change
    # Work already in the tree is not this session's to answer for; resume and compaction
    # fire SessionStart again, so only the first one sets the baseline.
    session_id = session_of(payload)
    state = load_state(session_id)
    if "baseline" not in state:
        state.update(base=base, baseline=baseline_of(root, rows))
        save_state(session_id, state)
    text = project_instructions(root)
    if TOOLBOX_HEADING in text or TOOLBOX_OPT_OUT in text:
        return
    print(TOOLBOX_HINT)


def log_error(exc: BaseException) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {type(exc).__name__}: {exc}\n")
    except OSError:
        pass


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else ""
    if command not in ("stop", "session-start"):
        sys.stderr.write(__doc__)
        return 2
    if os.environ.get("LEAVE_IT_SMALLER_DISABLE"):
        return 0
    payload = read_payload()
    try:
        if OPT_OUT in project_instructions(payload.get("cwd") or os.getcwd()):
            return 0
        if command == "stop":
            run_stop(payload)
        else:
            run_session_start(payload)
    except Exception as exc:  # noqa: BLE001 - a hook must never break the session
        log_error(exc)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
