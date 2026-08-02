#!/usr/bin/env bash
# PreToolUse hook (matcher: Task) — journalise chaque invocation de sous-agent.
# Ne bloque jamais l'appel : c'est un journal, pas une limite. Toujours exit 0.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null)"
LOG_DIR="${SCRIPT_DIR}/../logs"
LOG_FILE="${LOG_DIR}/agents.log"

mkdir -p "$LOG_DIR" 2>/dev/null || true

input="$(cat 2>/dev/null || true)"

# Extraction du subagent_type sans dépendance à jq : simple grep/sed sur le JSON brut reçu sur stdin.
subagent_type="$(printf '%s' "$input" \
  | grep -o '"subagent_type"[[:space:]]*:[[:space:]]*"[^"]*"' 2>/dev/null \
  | head -n1 \
  | sed -E 's/.*"subagent_type"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')"

[ -n "$subagent_type" ] || subagent_type="unknown"

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

printf '%s subagent_type=%s\n' "$timestamp" "$subagent_type" >> "$LOG_FILE" 2>/dev/null || true

exit 0
