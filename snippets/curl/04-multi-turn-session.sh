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
TURN1=$(de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query":   { "text": "My name is Jordan and I work in fixed income. Remember that." },
  "session": "'"${ENGINE_PATH}"'/sessions/-"
}')
echo "${TURN1}" | extract_text

# Every chunk repeats sessionInfo; take it from the first one.
SESSION=$(echo "${TURN1}" | jq -r '.[0].sessionInfo.session')
echo
echo "== session: ${SESSION}"
echo
echo "== Turn 2 (same session) =="
de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query":   { "text": "What is my name and what asset class do I work in?" },
  "session": "'"${SESSION}"'"
}' | extract_text
