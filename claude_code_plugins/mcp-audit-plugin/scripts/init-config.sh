#!/usr/bin/env bash
# init-config.sh — create ~/.claude/mcp-audit/config.json interactively.
# Idempotent: never overwrites an existing config unless you pass --force.
set -euo pipefail

HOME_DIR="${MCP_AUDIT_HOME:-$HOME/.claude/mcp-audit}"
CFG="$HOME_DIR/config.json"

FORCE=0
SERVERS=""
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --servers=*) SERVERS="${arg#*=}" ;;
    -h|--help)
      echo "Usage: init-config.sh [--servers=cookiev2,atlassian,asana] [--force]"
      exit 0 ;;
  esac
done

mkdir -p "$HOME_DIR"

if [[ -f "$CFG" && "$FORCE" -ne 1 ]]; then
  echo "Config already exists: $CFG"
  echo "Current servers: $(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("servers"))' "$CFG" 2>/dev/null || echo '?')"
  echo "Edit it directly, or re-run with --force to recreate."
  exit 0
fi

if [[ -z "$SERVERS" ]]; then
  read -r -p "Which MCP servers to audit? (comma-separated, e.g. cookiev2,atlassian,asana): " SERVERS
fi

# Build a JSON array from the comma-separated list.
JSON_SERVERS=$(python3 - "$SERVERS" <<'PY'
import json, sys
raw = sys.argv[1]
items = [s.strip() for s in raw.split(",") if s.strip()]
print(json.dumps(items))
PY
)

cat > "$CFG" <<EOF
{
  "servers": $JSON_SERVERS,
  "enabled": true,
  "truncate_bytes": 2048,
  "log_path": "$HOME_DIR/mcp-invocations.jsonl"
}
EOF

echo "Wrote $CFG"
echo "Auditing servers: $JSON_SERVERS"
echo "Log file: $HOME_DIR/mcp-invocations.jsonl"
