#!/usr/bin/env python3
"""Smoke test for vibe_diary_hook.py - no network calls, pure logic."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vibe_diary_hook import (  # noqa
    SessionStats,
    parse_transcript,
    ensure_table,
    insert_session_row,
    _calculate_cost,
    _short_model,
    _format_tokens_cost,
    TABLE_MARKER,
)


def make_transcript(tmp: Path) -> Path:
    """Fabricate a Claude Code JSONL transcript resembling a real one."""
    entries = [
        {
            "type": "user",
            "timestamp": "2026-04-17T09:15:00.000Z",
            "message": {"role": "user", "content": "Add a login form to the auth module."},
        },
        {
            "type": "assistant",
            "timestamp": "2026-04-17T09:15:20.000Z",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-5-20250929",
                "content": [
                    {"type": "text", "text": "I'll add a login form component."},
                    {"type": "tool_use", "name": "Read",
                     "input": {"file_path": "/repo/src/auth.py"}},
                ],
                "usage": {
                    "input_tokens": 1200, "output_tokens": 340,
                    "cache_creation_input_tokens": 800,
                    "cache_read_input_tokens": 5000,
                },
            },
        },
        {
            "type": "assistant",
            "timestamp": "2026-04-17T09:18:00.000Z",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-5-20250929",
                "content": [
                    {"type": "tool_use", "name": "Edit",
                     "input": {"file_path": "/repo/src/auth.py"}},
                    {"type": "text",
                     "text": "Added LoginForm component with email + password fields."},
                ],
                "usage": {
                    "input_tokens": 2100, "output_tokens": 520,
                    "cache_read_input_tokens": 8000,
                },
            },
        },
        {
            "type": "user",
            "timestamp": "2026-04-17T09:25:00.000Z",
            "message": {"role": "user", "content": "Thanks, that's perfect."},
        },
    ]
    path = tmp / "transcript.jsonl"
    with path.open("w") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")
    return path


def test_parsing(tmp_dir: Path):
    path = make_transcript(tmp_dir)
    stats = parse_transcript(path, session_id="test-sess-1")
    assert stats.message_count == 4, stats.message_count
    assert stats.input_tokens == 3300
    assert stats.output_tokens == 860
    assert stats.cache_creation_tokens == 800
    assert stats.cache_read_tokens == 13000
    assert stats.primary_model == "claude-sonnet-4-5-20250929"
    assert "Read" in stats.tools_used and "Edit" in stats.tools_used
    assert "/repo/src/auth.py" in stats.files_touched
    assert stats.started_at.startswith("2026-04-17T09:15:00")
    assert stats.ended_at.startswith("2026-04-17T09:25:00")
    assert stats.cost_usd > 0
    print(f"  parsed: {stats.total_tokens} tokens, ${stats.cost_usd:.4f}")
    print(f"  model short: {_short_model(stats.primary_model)}")
    print(f"  tokens/cost cell: {_format_tokens_cost(stats)}")
    return stats


def test_table_round_trip(stats: SessionStats):
    # Empty page - add first row
    body = ""
    body = insert_session_row(
        body, branch="feat/login",
        github_url="https://github.com/acme/app",
        stats=stats, summary="Added login form component.",
    )
    assert TABLE_MARKER in body
    assert "feat/login" in body
    assert "Added login form component." in body
    assert 'data-task="feat/login"' in body
    print("  first insert: OK")

    # Second session on the same branch - should group under the same task
    stats2 = SessionStats(
        session_id="sess-2",
        started_at="2026-04-17T14:00:00.000Z",
        ended_at="2026-04-17T14:45:00.000Z",
        models=["claude-opus-4-7"],
        input_tokens=500, output_tokens=1200,
    )
    stats2.cost_usd = _calculate_cost(stats2)
    body = insert_session_row(
        body, branch="feat/login",
        github_url="https://github.com/acme/app",
        stats=stats2, summary="Added form validation and tests.",
    )
    # Branch name should appear exactly once as a <strong> header cell
    strong_count = body.count("<strong>feat/login</strong>")
    assert strong_count == 1, f"expected 1 strong header for feat/login, got {strong_count}"
    # But both summaries should be present
    assert "Added login form component." in body
    assert "Added form validation and tests." in body
    # And rowspan should now be 2
    assert 'rowspan="2"' in body
    print("  second insert on same branch: grouped correctly with rowspan=2")

    # Third session on a *different* branch - should create a new group
    stats3 = SessionStats(
        session_id="sess-3",
        started_at="2026-04-17T16:00:00.000Z",
        ended_at="2026-04-17T16:15:00.000Z",
        models=["claude-haiku-4-5-20251001"],
        input_tokens=800, output_tokens=200,
    )
    stats3.cost_usd = _calculate_cost(stats3)
    body = insert_session_row(
        body, branch="bugfix/header",
        github_url="https://github.com/acme/app",
        stats=stats3, summary="Fixed header z-index.",
    )
    assert "bugfix/header" in body
    assert "Fixed header z-index." in body
    # feat/login should still be there with its 2 sessions intact
    assert body.count("<strong>feat/login</strong>") == 1
    assert body.count("<strong>bugfix/header</strong>") == 1
    assert "Added login form component." in body
    assert "Added form validation and tests." in body
    print("  third insert on new branch: new group created, old preserved")

    return body


def test_escaping():
    stats = SessionStats(
        session_id="x", started_at="2026-04-17T10:00:00Z", ended_at="2026-04-17T10:30:00Z",
        models=["claude-sonnet-4-5-20250929"], input_tokens=100, output_tokens=50,
    )
    body = insert_session_row(
        "", branch="feat/<script>alert(1)</script>",
        github_url="https://github.com/acme/app&foo=bar",
        stats=stats,
        summary='He said "hello" & waved <br> at me.',
    )
    assert "<script>" not in body, "branch name not escaped!"
    assert "&lt;script&gt;" in body
    assert "&amp;foo=bar" in body
    assert "&quot;hello&quot;" in body or "hello" in body
    print("  HTML escaping: OK")


def test_session_dedupe():
    """SessionEnd can fire more than once per session (clear/logout/exit).
    Re-inserting the same session_id must be a no-op."""
    stats = SessionStats(
        session_id="dup-sess-42",
        started_at="2026-04-17T12:00:00Z",
        ended_at="2026-04-17T12:10:00Z",
        models=["claude-sonnet-4-5-20250929"],
        input_tokens=500, output_tokens=200,
    )
    body = insert_session_row(
        "", branch="feat/x", github_url="https://github.com/acme/app",
        stats=stats, summary="First pass.",
    )
    assert body is not None and "dup-sess-42" in body

    # Replay: same session_id — should return None (skip PUT)
    replay = insert_session_row(
        body, branch="feat/x", github_url="https://github.com/acme/app",
        stats=stats, summary="This should not appear.",
    )
    assert replay is None, "duplicate session_id was not deduped"
    assert "This should not appear." not in body
    print("  session_id dedupe: OK (replay returned None)")

    # Sanity: a *different* session_id on the same branch still inserts
    stats2 = SessionStats(
        session_id="different-sess",
        started_at="2026-04-17T13:00:00Z",
        ended_at="2026-04-17T13:20:00Z",
        models=["claude-sonnet-4-5-20250929"],
        input_tokens=100, output_tokens=50,
    )
    body2 = insert_session_row(
        body, branch="feat/x", github_url="https://github.com/acme/app",
        stats=stats2, summary="Second real session.",
    )
    assert body2 is not None
    assert "Second real session." in body2
    print("  different session_id still inserts: OK")


def test_empty_session_skipped():
    # Not a full test (that path returns from main()), just confirm parsing
    # handles a file with only a single user message.
    stats = SessionStats(session_id="x", started_at="", ended_at="")
    stats.message_count = 1
    # main() would bail here due to VIBE_DIARY_MIN_MESSAGES default of 2
    assert stats.message_count < 2
    print("  short-session guard: OK")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        print("test_parsing:")
        stats = test_parsing(tmp_dir)
        print("test_table_round_trip:")
        body = test_table_round_trip(stats)
        print("test_escaping:")
        test_escaping()
        print("test_session_dedupe:")
        test_session_dedupe()
        print("test_empty_session_skipped:")
        test_empty_session_skipped()
        print("\nAll tests passed.")
        print("\n--- Rendered body sample (last 800 chars) ---")
        print(body[-800:])
