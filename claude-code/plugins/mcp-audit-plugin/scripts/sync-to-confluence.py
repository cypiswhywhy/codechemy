#!/usr/bin/env python3
"""
sync-to-confluence.py — push new MCP-audit rows to the shared Confluence table.

Reads the local JSONL log, joins each PreToolUse ("pre") line with its matching
PostToolUse ("post") line by tool_use_id, then appends one table row per call to
the Confluence page. Rows already synced (tracked locally) are skipped, so the
script is safe to run repeatedly and safe to run by multiple team members
against the same page.

Uses only the Python standard library (urllib) — no pip install required.

CONFIG (env vars; page defaults target the AIC4E log page):
  CONFLUENCE_BASE_URL   default https://pearson.atlassian.net/wiki
  CONFLUENCE_PAGE_ID    default 1221918747
  CONFLUENCE_EMAIL      your Atlassian account email        (required to push)
  CONFLUENCE_API_TOKEN  https://id.atlassian.com/manage-profile/security/api-tokens  (required to push)

Log location resolves the same way as the hook:
  MCP_AUDIT_HOME        default ~/.claude/mcp-audit

USAGE:
  python3 sync-to-confluence.py            # push new rows
  python3 sync-to-confluence.py --dry-run  # show what would be pushed, no write
  python3 sync-to-confluence.py --limit 50 # cap rows this run
"""

import os
import sys
import json
import base64
import pathlib
import argparse
import urllib.request
import urllib.error
from html import escape

TABLE_MARKER = "mcp-audit-log-table"  # ac:parameter tag we plant to find our table

COLUMNS = [
    ("ts", "Timestamp (UTC)"),
    ("user", "User"),
    ("host", "Host"),
    ("server", "Server"),
    ("tool", "Tool"),
    ("status", "Status"),
    ("duration_ms", "Duration (ms)"),
    ("session_id", "Session"),
    ("cwd", "cwd"),
    ("tool_input", "Input (truncated)"),
    ("tool_use_id", "tool_use_id"),
]


def audit_home() -> pathlib.Path:
    h = os.environ.get("MCP_AUDIT_HOME")
    if h:
        return pathlib.Path(os.path.expanduser(h))
    return pathlib.Path(os.path.expanduser("~/.claude/mcp-audit"))


def load_rows(log_path: pathlib.Path):
    """Join pre/post lines by tool_use_id into one row dict per call."""
    if not log_path.exists():
        return []
    calls = {}
    orphan_index = 0
    order = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            tuid = rec.get("tool_use_id") or ""
            # Fall back to a synthetic key so calls without an id still surface.
            key = tuid or ("noid-%s-%d" % (rec.get("ts", ""), orphan_index))
            if not tuid:
                orphan_index += 1
            if key not in calls:
                calls[key] = {}
                order.append(key)
            c = calls[key]
            if rec.get("event") == "pre":
                c.update({
                    "ts": rec.get("ts", ""),
                    "user": rec.get("user", ""),
                    "host": rec.get("host", ""),
                    "server": rec.get("server", ""),
                    "tool": rec.get("tool_name", ""),
                    "session_id": rec.get("session_id", ""),
                    "cwd": rec.get("cwd", ""),
                    "tool_input": rec.get("tool_input", ""),
                    "tool_use_id": tuid,
                })
            elif rec.get("event") == "post":
                c.setdefault("ts", rec.get("ts", ""))
                c.setdefault("server", rec.get("server", ""))
                c.setdefault("tool", rec.get("tool_name", ""))
                c.setdefault("session_id", rec.get("session_id", ""))
                c["status"] = rec.get("status", "")
                c["duration_ms"] = rec.get("duration_ms", "")
                c["tool_use_id"] = tuid
    return [calls[k] for k in order]


def row_key(row) -> str:
    """Stable identity for dedup. tool_use_id when present, else ts+tool."""
    return row.get("tool_use_id") or ("%s|%s" % (row.get("ts", ""), row.get("tool", "")))


def cell(row, field) -> str:
    v = row.get(field, "")
    if field == "tool_input" and not isinstance(v, str):
        try:
            v = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            v = str(v)
    if v is None:
        v = ""
    return escape(str(v))


def build_rows_html(rows) -> str:
    out = []
    for r in rows:
        cells = "".join("<td><p>%s</p></td>" % cell(r, f) for f, _ in COLUMNS)
        out.append("<tr>%s</tr>" % cells)
    return "".join(out)


def build_table_html(rows) -> str:
    header = "".join("<th><p><strong>%s</strong></p></th>" % escape(t) for _, t in COLUMNS)
    marker = ('<ac:structured-macro ac:name="anchor">'
              '<ac:parameter ac:name="">%s</ac:parameter>'
              '</ac:structured-macro>') % TABLE_MARKER
    return (
        "<p>%s</p>"
        "<table data-layout=\"full-width\"><tbody>"
        "<tr>%s</tr>%s"
        "</tbody></table>"
    ) % (marker, header, build_rows_html(rows))


def http(method, url, email=None, token=None, data=None):
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if email and token:
        cred = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
        headers["Authorization"] = "Basic %s" % cred
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, (json.loads(payload) if payload else {})
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        raise SystemExit("HTTP %s from %s\n%s" % (e.code, url, detail))
    except urllib.error.URLError as e:
        raise SystemExit("Network error contacting %s: %s" % (url, e))


def get_page(base_url, page_id, email, token):
    url = "%s/api/v2/pages/%s?body-format=storage" % (base_url.rstrip("/"), page_id)
    _, data = http("GET", url, email, token)
    return data


def update_page(base_url, page_id, title, version, body_value, email, token):
    url = "%s/api/v2/pages/%s" % (base_url.rstrip("/"), page_id)
    data = {
        "id": str(page_id),
        "status": "current",
        "title": title,
        "body": {"representation": "storage", "value": body_value},
        "version": {"number": version + 1, "message": "mcp-audit sync"},
    }
    return http("PUT", url, email, token, data)


def splice_rows(existing_body: str, rows) -> str:
    """Append rows to our table if present, else create the table."""
    rows_html = build_rows_html(rows)
    if TABLE_MARKER in existing_body and "</tbody>" in existing_body:
        # Insert before the LAST </tbody> (our table is appended at page end).
        idx = existing_body.rfind("</tbody>")
        return existing_body[:idx] + rows_html + existing_body[idx:]
    return (existing_body or "") + build_table_html(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    base = audit_home()
    log_path = pathlib.Path(os.path.expanduser(
        os.environ.get("MCP_AUDIT_LOG", str(base / "mcp-invocations.jsonl"))))
    synced_path = base / "synced.txt"

    all_rows = load_rows(log_path)
    synced = set()
    if synced_path.exists():
        synced = set(x.strip() for x in synced_path.read_text().splitlines() if x.strip())

    new_rows = [r for r in all_rows if row_key(r) not in synced]
    if args.limit and len(new_rows) > args.limit:
        new_rows = new_rows[: args.limit]

    if not new_rows:
        print("Nothing new to sync (%d calls in log, all already synced)." % len(all_rows))
        return

    print("Found %d new call(s) to sync." % len(new_rows))

    if args.dry_run:
        for r in new_rows:
            print("  %s  %s  %s  %sms  %s" % (
                r.get("ts", ""), r.get("server", ""), r.get("tool", ""),
                r.get("duration_ms", "?"), r.get("status", "")))
        print("\n[dry-run] Table HTML preview:\n")
        print(build_table_html(new_rows[:3]))
        return

    base_url = os.environ.get("CONFLUENCE_BASE_URL", "https://pearson.atlassian.net/wiki")
    page_id = os.environ.get("CONFLUENCE_PAGE_ID", "1221918747")
    email = os.environ.get("CONFLUENCE_EMAIL")
    token = os.environ.get("CONFLUENCE_API_TOKEN")
    if not email or not token:
        raise SystemExit(
            "Set CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN to push. "
            "Create a token at https://id.atlassian.com/manage-profile/security/api-tokens "
            "(or use --dry-run to preview without pushing).")

    page = get_page(base_url, page_id, email, token)
    title = page.get("title", "Cookie's MCPs invocation log")
    version = page.get("version", {}).get("number", 1)
    body = page.get("body", {}).get("storage", {}).get("value", "") or ""

    new_body = splice_rows(body, new_rows)
    update_page(base_url, page_id, title, version, new_body, email, token)

    with open(synced_path, "a", encoding="utf-8") as f:
        for r in new_rows:
            f.write(row_key(r) + "\n")

    print("Synced %d row(s) to %s/pages/%s (version %d)."
          % (len(new_rows), base_url.rstrip("/"), page_id, version + 1))


if __name__ == "__main__":
    main()
