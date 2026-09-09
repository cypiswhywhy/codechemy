# Vibe-coding diary hook for Claude Code

A `SessionEnd` hook that logs each Claude Code session to a Confluence page,
grouped by task (= git branch). After each session you get a new row with
start/end times, model, token usage, cost, and an auto-generated summary.

## What it looks like

The page contains a single table. Sessions on the same branch are grouped
under one Task row via `rowspan`:

| Task (branch) | Repo | Session start | Session end | Model | Summary | Tokens / cost |
|---|---|---|---|---|---|---|
| **feat/login** | acme/app | 2026-04-17 09:15 | 2026-04-17 09:25 | sonnet-4-5 | Added login form component. | 18.0k tok / $0.030 |
|  |  | 2026-04-17 14:00 | 2026-04-17 14:45 | opus-4-7 | Added form validation and tests. | 1.7k tok / $0.098 |
| **bugfix/header** | acme/app | 2026-04-17 16:00 | 2026-04-17 16:15 | haiku-4-5 | Fixed header z-index. | 1.0k tok / $0.002 |

## How it works

1. Claude Code fires `SessionEnd` with `{session_id, transcript_path, cwd, reason}` on stdin.
2. The hook parses the JSONL transcript for: start/end timestamps, model(s),
   token counts (input / output / cache create / cache read), tools used,
   and files touched.
3. It computes cost from per-model rates (see `MODEL_PRICES` in the script).
4. It **double-forks and detaches**, so Claude Code's shutdown isn't blocked
   by the network round-trips that follow. The rest happens in the background.
5. It asks Claude Haiku for a 1–2 sentence summary by shelling out to
   `claude -p` — this uses your Claude Code subscription, no separate API
   key needed. (A `VIBE_DIARY_SKIP=1` env var on the subprocess stops the
   sub-session's own SessionEnd from re-entering this hook.)
6. It reads the current Confluence page, finds the row for the current branch
   (or creates one), appends this session beneath it, and PUTs the updated
   body back. If the PUT returns HTTP 409 (two sessions ending concurrently,
   both racing on the same page version), it re-fetches and retries with
   jittered backoff — up to 4 attempts.
7. Each session row carries `data-session="<id>"`. If `SessionEnd` fires
   more than once for the same session (e.g. `/clear` then `exit`), the
   second firing is a no-op.

## Setup

### 1. Place the script

```bash
mkdir -p ~/.claude/hooks
cp vibe_diary_hook.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/vibe_diary_hook.py
```

### 2. Create a Confluence API token

Go to <https://id.atlassian.com/manage-profile/security/api-tokens> and
create one. You'll also need the numeric ID of your diary page — open the
page and look at the URL: `.../pages/123456789/Page+Title`.

### 3. Put credentials in an env file

Create `~/.claude/vibe-diary.env`:

```sh
CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_EMAIL=you@example.com
CONFLUENCE_API_TOKEN=your-atlassian-api-token
CONFLUENCE_PAGE_ID=123456789
```

Lock it down: `chmod 600 ~/.claude/vibe-diary.env`.

(You can also export these from your shell instead; the script checks both.)

No Anthropic API key is needed — the summary call uses the `claude` CLI,
which picks up whatever auth Claude Code is using (your subscription or an
API key configured for the CLI). Just make sure `claude` is on your PATH.

### 4. Register the hook

Add to `~/.claude/settings.json` (or your project's `.claude/settings.json`
if you only want it for one project):

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/vibe_diary_hook.py"
          }
        ]
      }
    ]
  }
}
```

After editing, restart Claude Code or run `/hooks` to review and apply.

### 5. Test it

Open a throwaway session in a git repo, ask Claude to do something small,
then exit. Check `~/.claude/vibe-diary.log` for either a success line or
an error. Then refresh your Confluence page.

## Configuration knobs

Environment variables the script reads:

| Variable | Purpose | Default |
|---|---|---|
| `VIBE_DIARY_LOG` | Path to the log file | `~/.claude/vibe-diary.log` |
| `VIBE_DIARY_MIN_MESSAGES` | Skip sessions shorter than this (user + assistant combined) | `2` |
| `VIBE_DIARY_SKIP` | Set internally on the `claude -p` subprocess to prevent the sub-session's SessionEnd from re-entering this hook. Set it yourself to disable the hook for a single session. | unset |

## Design notes

- **Non-blocking in two senses.** (1) The hook always exits 0, even on
  failure, so a broken Confluence token never prevents Claude Code from
  shutting down cleanly. (2) It double-forks before the slow bits (summary
  call + Confluence round-trips), so the parent returns in milliseconds
  and you never sit looking at a hung exit. All errors go to the log file.
- **Uses your Claude Code subscription for summaries.** The hook shells out
  to `claude -p` rather than calling the Anthropic REST API directly, so
  you don't need to manage a separate API key. A `VIBE_DIARY_SKIP=1` env
  var on the subprocess prevents infinite recursion (the sub-session's own
  SessionEnd would otherwise re-enter this hook).
- **Stdlib only.** No `requests`, no `atlassian-python-api` — the script uses
  `urllib` so you don't need `pip install` anything.
- **Dedupes on session_id.** Each row carries `data-session="<id>"`.
  SessionEnd fires on `clear`, `logout`, `exit`, etc., sometimes more than
  once per session; replays are a no-op.
- **Handles Confluence version conflicts.** If two sessions end concurrently,
  one will race the other on the page version and get HTTP 409. The hook
  re-fetches and retries with jittered backoff (up to 4 attempts).
- **Round-trippable markup.** Each row carries `data-task="<branch>"` and
  `data-github="<url>"` attributes so the hook can parse its own prior
  output. If you manually edit rows in Confluence the hook will try to
  preserve them, but it's safer to use the table as read-mostly.
- **Cost is an estimate.** The `SessionEnd` hook input doesn't currently
  include token/cost data directly (see
  [claude-code#11008](https://github.com/anthropics/claude-code/issues/11008)),
  so we compute it from transcript usage blocks × per-model rates. Update
  `MODEL_PRICES` if Anthropic changes pricing.
- **Why not a skill?** Skills are model-facing instruction bundles — they
  rely on Claude remembering to use them. A hook is a deterministic shell
  command Claude Code runs for you, which is what you want for "every
  session, no exceptions."

## Troubleshooting

- **Nothing happens:** check `~/.claude/vibe-diary.log`. Most likely a
  missing env var or a bad `CONFLUENCE_PAGE_ID`. Because the hook
  daemonizes, the foreground process exits instantly either way — the
  log is the source of truth.
- **"Missing env vars":** make sure `~/.claude/vibe-diary.env` exists and
  is readable. The script calls `os.environ.setdefault`, so values already
  in your shell env win over the file.
- **Summaries say `(no summary available)`:** the `claude` CLI isn't on
  PATH, or it couldn't auth. Run `claude -p 'hello'` in a terminal to
  confirm it works standalone; fix whichever of those is broken.
- **Sessions aren't grouping:** the branch name must match exactly. If you
  rename a branch mid-task, the old row stays under the old name. You can
  manually merge the rows in Confluence.
- **Wrong cost:** update the rates in `MODEL_PRICES`. The hook falls back
  to `$0.00` (and logs a warning) for models it doesn't recognize.
