#!/usr/bin/env bash
# 28 — Native A2A: send one message and wait for the complete response.
# Usage: ./28-a2a-message-send.sh <agent-id> "your message" [registry-a2a-url]
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

AGENT_ID="${1:?usage: $0 <agent-id> \"message\" [registry-a2a-url]}"
MESSAGE="${2:?usage: $0 <agent-id> \"message\" [registry-a2a-url]}"
if [[ -n "${3:-}" ]]; then
  A2A_BASE="$3"
else
  PROJECT_NUMBER="${PROJECT_NUMBER:-$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')}"
  A2A_BASE="https://${DE_HOST}/v1/projects/${PROJECT_NUMBER}/locations/${LOCATION}/collections/default_collection/engines/${APP_ID}/assistants/${ASSISTANT_ID}/agents/${AGENT_ID}/a2a"
fi
A2A_BASE="${A2A_BASE%/}"
MESSAGE_ID="$(new_message_id)"
BODY=$(jq -nc --arg text "${MESSAGE}" --arg id "${MESSAGE_ID}" \
  '{message: {role: "ROLE_USER", content: [{text: $text}], messageId: $id}}')

curl -sS --fail-with-body --max-time 600 -X POST \
  "${A2A_BASE}/v1/message:send" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d "${BODY}"
