#!/usr/bin/env bash
# ------------------------------------------------------------------
# 04 — Multi-turn conversation in one session.
# Turn 1 creates a session via the "-" placeholder; the session name
# comes back in sessionInfo.session. Turn 2 reuses it, so the
# assistant sees the history.
#
# Usage: ./04-multi-turn-session.sh
# Requires: jq
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

extract_text() {
  jq -r '[ .[] | .answer.replies[]? | .groundedContent.content
           | select(. != null and .thought != true) | .text // empty ] | join("")'
}

echo "== Turn 1 =="
TURN1_BODY=$(jq -nc --arg session "${ENGINE_PATH}/sessions/-" \
  '{query: {text: "My name is Jordan and I work in fixed income. Remember that."}, session: $session}')
TURN1=$(de_post "${ASSISTANT_PATH}:streamAssist" "${TURN1_BODY}")
echo "${TURN1}" | extract_text

# v1 sends sessionInfo on the final response object.
SESSION=$(echo "${TURN1}" | jq -er '[.[] | .sessionInfo.session // empty] | last')
echo
echo "== session: ${SESSION}"
echo
echo "== Turn 2 (same session) =="
TURN2_BODY=$(jq -nc --arg session "${SESSION}" \
  '{query: {text: "What is my name and what asset class do I work in?"}, session: $session}')
de_post "${ASSISTANT_PATH}:streamAssist" "${TURN2_BODY}" | extract_text
