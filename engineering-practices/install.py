#!/usr/bin/env python3
"""Install or remove the engineering-practices bundle for Claude Code. Stdlib only, idempotent.

    python3 install.py              # install or update
    python3 install.py --uninstall  # remove everything this installer put in place
    python3 install.py --status     # installed version vs the bundle's

The bundle is data; this installer is generic over it:

    practices/*.md          concatenated (sorted) into one managed block in CLAUDE.md
    hooks/<name>/hook.json  {"script": "...py", "events": {"Stop": "sub", ...}, "timeout": 30}
                            the script is copied to hooks/ and registered per event
    skills/<name>/           copied into skills/<name>/
    VERSION                 the bundle version, stamped into the block and the state file

Everything is a copy: `git pull` on the bundle changes nothing until this runs again. What was
installed, and at which version, is recorded in ${CLAUDE_CONFIG_DIR}/engineering-practices.json;
`--status` prints installed versus available. Existing content is preserved: the CLAUDE.md
block is replaced in place, other hooks in settings.json are untouched, and settings.json is
backed up before it is changed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
NAME = "engineering-practices"
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")

PRACTICES = sorted((BUNDLE / "practices").glob("*.md"))
HOOKS = sorted((BUNDLE / "hooks").glob("*/hook.json"))
SKILLS = sorted(p.parent for p in (BUNDLE / "skills").glob("*/SKILL.md"))
VERSION = (BUNDLE / "VERSION").read_text().strip() if (BUNDLE / "VERSION").exists() else "0.0.0"

CLAUDE_MD = CONFIG_DIR / "CLAUDE.md"
HOOKS_DIR = CONFIG_DIR / "hooks"
SETTINGS = CONFIG_DIR / "settings.json"
SKILLS_DIR = CONFIG_DIR / "skills"
STATE_FILE = CONFIG_DIR / f"{NAME}.json"
STATE_DIRS = [CONFIG_DIR / p.parent.name for p in HOOKS]  # per-hook state, e.g. leave-it-smaller/

BEGIN = f"<!-- {NAME}:begin"
END = f"<!-- {NAME}:end -->"
HEADER = (
    f"{BEGIN} v{VERSION} (managed block: install.py in {NAME}/ of the codechemy repo replaces "
    "it on reinstall; edit practices/*.md in the bundle, not this copy) -->"
)


def say(status: str, message: str) -> None:
    print(f"  {status:<9} {message}")


# ----- CLAUDE.md -------------------------------------------------------------


def managed_block() -> str:
    body = "\n\n".join(p.read_text().strip() for p in PRACTICES)
    return f"{HEADER}\n{body}\n{END}\n"


def strip_block(text: str) -> str:
    start = text.find(BEGIN)
    if start < 0:
        return text
    end = text.find(END, start)
    if end < 0:
        return text
    end += len(END)
    before, after = text[:start].rstrip("\n"), text[end:].lstrip("\n")
    if not before:
        return after
    return before + ("\n\n" + after if after else "\n")


def install_claude_md() -> None:
    existing = CLAUDE_MD.read_text() if CLAUDE_MD.exists() else ""
    rest = strip_block(existing).rstrip("\n")
    new = (rest + "\n\n" if rest else "") + managed_block()
    if new == existing:
        say("unchanged", str(CLAUDE_MD))
        return
    CLAUDE_MD.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_MD.write_text(new)
    say("updated" if BEGIN in existing else "added", f"{CLAUDE_MD} (managed block, {len(PRACTICES)} practice file(s))")


def uninstall_claude_md() -> None:
    if not CLAUDE_MD.exists() or BEGIN not in CLAUDE_MD.read_text():
        say("absent", f"{CLAUDE_MD} has no managed block")
        return
    rest = strip_block(CLAUDE_MD.read_text())
    if rest.strip():
        CLAUDE_MD.write_text(rest)
        say("removed", f"managed block from {CLAUDE_MD}")
    else:
        CLAUDE_MD.unlink()
        say("removed", f"{CLAUDE_MD} (held only the managed block)")


# ----- settings.json ---------------------------------------------------------


def load_settings() -> dict:
    if not SETTINGS.exists():
        return {}
    try:
        data = json.loads(SETTINGS.read_text())
    except ValueError as exc:
        sys.exit(f"error: {SETTINGS} is not valid JSON ({exc}); fix it and re-run")
    if not isinstance(data, dict):
        sys.exit(f"error: {SETTINGS} must hold a JSON object")
    return data


def write_settings(before: dict, after: dict) -> bool:
    if before == after:
        return False
    if SETTINGS.exists():
        backup = SETTINGS.with_name(f"settings.json.{NAME}.{time.strftime('%Y%m%d-%H%M%S')}.bak")
        shutil.copy2(SETTINGS, backup)
        say("backup", str(backup))
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(after, indent=2) + "\n")
    return True


def hook_manifests() -> list[dict]:
    manifests = []
    for manifest_path in HOOKS:
        manifest = json.loads(manifest_path.read_text())
        script = manifest_path.parent / manifest["script"]
        if not script.exists():
            sys.exit(f"error: {manifest_path} names a missing script {manifest['script']}")
        manifests.append({**manifest, "source": script, "target": HOOKS_DIR / manifest["script"]})
    return manifests


def is_ours(hook: dict, scripts: set[str]) -> bool:
    command = str(hook.get("command", ""))
    return any(f"{HOOKS_DIR.name}/{script}" in command for script in scripts)


def without_our_hooks(groups: list, scripts: set[str]) -> list:
    kept = []
    for group in groups:
        hooks = [h for h in group.get("hooks", []) if not is_ours(h, scripts)]
        if hooks or "hooks" not in group:
            kept.append({**group, "hooks": hooks} if "hooks" in group else group)
    return kept


def install_settings(manifests: list[dict]) -> None:
    scripts = {m["script"] for m in manifests}
    before = load_settings()
    after = json.loads(json.dumps(before))
    hooks = after.setdefault("hooks", {})
    events = sorted({event for m in manifests for event in m["events"]})
    for event in events:
        groups = without_our_hooks(hooks.get(event, []), scripts)
        for m in manifests:
            if event in m["events"]:
                entry = {"type": "command", "command": f'python3 "{m["target"]}" {m["events"][event]}'}
                if "timeout" in m:
                    entry["timeout"] = m["timeout"]
                groups.append({"hooks": [entry]})
        hooks[event] = groups
    changed = write_settings(before, after)
    say("updated" if changed else "unchanged", f"{SETTINGS} ({', '.join(events)})")


def uninstall_settings(manifests: list[dict]) -> None:
    scripts = {m["script"] for m in manifests}
    before = load_settings()
    after = json.loads(json.dumps(before))
    hooks = after.get("hooks", {})
    for event in list(hooks):
        hooks[event] = without_our_hooks(hooks[event], scripts)
        if not hooks[event]:
            del hooks[event]
    if "hooks" in after and not after["hooks"]:
        del after["hooks"]
    say("removed" if write_settings(before, after) else "absent", f"hook registrations in {SETTINGS}")


# ----- state -----------------------------------------------------------------


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def bundle_commit() -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(BUNDLE), "log", "-1", "--format=%h", "--", "."],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    dirty = subprocess.run(
        ["git", "-C", str(BUNDLE), "status", "--porcelain", "--", "."],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    return proc.stdout.strip() + ("-dirty" if dirty else "")


def write_state(manifests: list[dict], skills: list[str]) -> None:
    state = {
        "version": VERSION,
        "commit": bundle_commit(),
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": str(BUNDLE),
        "practices": [p.name for p in PRACTICES],
        "hooks": [m["script"] for m in manifests],
        "skills": skills,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


# ----- files -----------------------------------------------------------------


def install_hook_scripts(manifests: list[dict]) -> None:
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for m in manifests:
        if m["target"].exists() and m["target"].read_bytes() == m["source"].read_bytes():
            say("unchanged", str(m["target"]))
        else:
            shutil.copy2(m["source"], m["target"])
            say("copied", str(m["target"]))
        m["target"].chmod(0o755)


def install_skills(previous: dict) -> list[str]:
    """Copy each skill directory; returns the names now owned by this install."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    owned = set(previous.get("skills", []))
    installed = []
    for source in SKILLS:
        target = SKILLS_DIR / source.name
        if target.exists() and source.name not in owned:
            say("skipped", f"{target} exists and was not installed by this bundle; leaving it alone")
            continue
        if target.is_dir() and same_tree(source, target):
            say("unchanged", str(target))
        else:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
            say("copied", str(target))
        installed.append(source.name)
    return installed


def same_tree(a: Path, b: Path) -> bool:
    files_a = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    return files_a == files_b and all((a / f).read_bytes() == (b / f).read_bytes() for f in files_a)


def remove_path(path: Path, label: str) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        say("removed", label)
    elif path.is_dir():
        shutil.rmtree(path)
        say("removed", label)
    else:
        say("absent", label)


def run_tests() -> list:
    """Run the bundle's test suites against the fresh install; return the ones that failed."""
    if os.environ.get("ENGINEERING_PRACTICES_NO_SELFTEST"):
        return []  # set by test_install.py, which would otherwise recurse into itself
    tests = sorted(BUNDLE.glob("test_*.py")) + sorted(BUNDLE.glob("hooks/*/test_*.py"))
    failed = []
    for test in tests:
        proc = subprocess.run([sys.executable, str(test), "-q"], capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            failed.append(test)
            print(proc.stderr[-1500:])
    if failed:
        say("FAILED", "self-test: " + ", ".join(str(t.relative_to(BUNDLE)) for t in failed))
    else:
        say("passed", f"self-test ({len(tests)} suite(s))")
    return failed


# ----- entry points ----------------------------------------------------------


def install() -> None:
    if not PRACTICES:
        sys.exit(f"error: no practices/*.md in {BUNDLE}")
    manifests = hook_manifests()
    previous = load_state()
    was = f" (was v{previous['version']})" if previous.get("version") else ""
    print(f"Installing {NAME} v{VERSION}{was} into {CONFIG_DIR}")
    install_claude_md()
    install_hook_scripts(manifests)
    install_settings(manifests)
    skills = install_skills(previous)
    write_state(manifests, skills)
    if run_tests():
        sys.exit(f"\nInstalled {NAME} v{VERSION}, but its self-test failed (see above). Fix that before relying on it.")
    print(f"\nInstalled {NAME} v{VERSION}. Restart Claude Code (or run /hooks in a session) to load the hooks.")


def uninstall() -> None:
    manifests = hook_manifests()
    previous = load_state()
    print(f"Removing {NAME}" + (f" v{previous['version']}" if previous.get("version") else "") + f" from {CONFIG_DIR}")
    uninstall_settings(manifests)
    uninstall_claude_md()
    for m in manifests:
        remove_path(m["target"], str(m["target"]))
    for source in SKILLS:
        target = SKILLS_DIR / source.name
        if source.name in previous.get("skills", []):
            remove_path(target, str(target))
        else:
            say("absent", f"{target} (not installed by this bundle)")
    for state in STATE_DIRS:
        remove_path(state, f"{state} (hook state + log)")
    remove_path(STATE_FILE, str(STATE_FILE))
    print("\nDone. Restart Claude Code to drop the hooks.")


def status() -> None:
    state = load_state()
    if not state:
        print(f"{NAME}: not installed in {CONFIG_DIR} (available: v{VERSION} at {BUNDLE})")
        return
    print(f"{NAME} in {CONFIG_DIR}")
    print(f"  installed  v{state.get('version')}  commit {state.get('commit') or '?'}  at {state.get('installed_at')}")
    print(f"  available  v{VERSION}  commit {bundle_commit() or '?'}  at {BUNDLE}")
    print(f"  practices  {', '.join(state.get('practices', [])) or '-'}")
    print(f"  hooks      {', '.join(state.get('hooks', [])) or '-'}")
    print(f"  skills     {', '.join(state.get('skills', [])) or '-'}")
    if state.get("version") != VERSION:
        print("  -> run: make install-engineering-practices")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--uninstall"]:
        uninstall()
    elif args == ["--status"]:
        status()
    elif not args:
        install()
    else:
        sys.exit(__doc__)
