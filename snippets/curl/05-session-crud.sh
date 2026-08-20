#!/usr/bin/env bash
# ------------------------------------------------------------------
# 05 — Session management: list, get, pin, delete.
#
# Usage:
#   ./05-session-crud.sh list
#   ./05-session-crud.sh get    <session-id>
#   ./05-session-crud.sh pin    <session-id>
#   ./05-session-crud.sh delete <session-id>
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

ACTION="${1:-list}"
SESSION_ID="${2:-}"

case "${ACTION}" in
  list)
    # Newest first. filter= and orderBy= are supported (see docs/04-sessions.md).
    de_get "${ENGINE_PATH}/sessions?pageSize=10&orderBy=update_time%20desc"
    ;;
  get)
    : "${SESSION_ID:?usage: $0 get <session-id>}"
    # includeAnswerDetails=true also returns every turn's full answer.
    de_get "${ENGINE_PATH}/sessions/${SESSION_ID}?includeAnswerDetails=true"
    ;;
  pin)
    : "${SESSION_ID:?usage: $0 pin <session-id>}"
    curl -sS -X PATCH "${BASE_URL}/${ENGINE_PATH}/sessions/${SESSION_ID}?updateMask=isPinned" \
      -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
      -H "X-Goog-User-Project: ${PROJECT_ID}" \
      -d '{"isPinned": true}'
    ;;
  delete)
    : "${SESSION_ID:?usage: $0 delete <session-id>}"
    curl -sS -X DELETE "${BASE_URL}/${ENGINE_PATH}/sessions/${SESSION_ID}" \
      -H "Authorization: Bearer ${TOKEN}" -H "X-Goog-User-Project: ${PROJECT_ID}"
    ;;
  *)
    echo "unknown action: ${ACTION}" >&2; exit 1;;
esac
