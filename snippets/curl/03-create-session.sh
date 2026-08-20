#!/usr/bin/env bash
# ------------------------------------------------------------------
# 03 — Create a session explicitly.
# You rarely need this: streamAssist auto-creates a session when you
# omit "session" or pass ".../sessions/-". Explicit creation is
# useful when you want to upload context files BEFORE the first
# query, or control the display name.
#
# Usage: ./03-create-session.sh ["display name"]
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

DISPLAY_NAME="${1:-api-created-session}"

de_post "${ENGINE_PATH}/sessions" '{
  "displayName": "'"${DISPLAY_NAME}"'"
}'
