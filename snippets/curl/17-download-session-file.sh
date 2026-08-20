#!/usr/bin/env bash
# ------------------------------------------------------------------
# 17 — Download a file from a session.
# Generated images/videos/audio and uploaded files all live in the
# session's context files, addressed by fileId.
#
# GOTCHAS (see docs/08-files.md):
#   * alt=media is required, otherwise you get an empty 200.
#   * The response is a 302 redirect — curl needs -L to follow it.
#
# Usage: ./17-download-session-file.sh <session-id> <file-id> <output-path>
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

SESSION_ID="${1:?usage: $0 <session-id> <file-id> <output-path>}"
FILE_ID="${2:?usage: $0 <session-id> <file-id> <output-path>}"
OUT="${3:?usage: $0 <session-id> <file-id> <output-path>}"

curl -sS -L -o "${OUT}" \
  "${BASE_URL}/${ENGINE_PATH}/sessions/${SESSION_ID}:downloadFile?fileId=${FILE_ID}&alt=media" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}"

ls -la "${OUT}"
file "${OUT}" 2>/dev/null || true
