#!/usr/bin/env bash
# ------------------------------------------------------------------
# 24 — Native A2A: send a message DIRECTLY to one agent.
# Bypasses the streamAssist orchestrator entirely: no routing
# heuristics, no chit-chat classifier — the agent always receives
# the message. Response streams A2A messages whose metadata embeds
# the familiar answer.replies structure; message.contextId is a
# session name you can pass back for multi-turn.
#
# Usage: ./24-a2a-message-stream.sh <agent-id> "your message"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

AGENT_ID="${1:?usage: $0 <agent-id> \"message\"}"
MESSAGE="${2:?usage: $0 <agent-id> \"message\"}"

curl -sS --max-time 600 -X POST \
  "https://${DE_HOST}/v1/${ASSISTANT_PATH}/agents/${AGENT_ID}/a2a/v1/message:stream" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "message": {
      "role": "ROLE_USER",
      "content": [ { "text": "'"${MESSAGE}"'" } ],
      "messageId": "msg-'"$(date +%s)"'"
    }
  }'
