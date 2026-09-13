#!/usr/bin/env bash
# ------------------------------------------------------------------
# 19 — Force an answer for "chit-chat" queries.
# By default a query classifier SKIPS anything that doesn't look
# answer-seeking ("hello", "thanks") with state=SKIPPED and reason
# NON_ASSIST_SEEKING_QUERY_IGNORED — even when you pinned an agent.
# assistSkippingMode=REQUEST_ASSIST disables that classifier.
#
# Run without arguments to see both behaviors side by side.
#
# Usage: ./19-assist-skipping-mode.sh ["query"]
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

QUERY="${1:-hello}"

echo "== Default behavior (likely SKIPPED for greetings) =="
DEFAULT_BODY=$(jq -nc --arg query "${QUERY}" \
  '{query: {text: $query}, isSessionLess: true}')
de_post_alpha "${ASSISTANT_PATH}:streamAssist" "${DEFAULT_BODY}"
echo
echo "== With assistSkippingMode=REQUEST_ASSIST =="
FORCED_BODY=$(jq -nc --arg query "${QUERY}" \
  '{query: {text: $query}, assistSkippingMode: "REQUEST_ASSIST", isSessionLess: true}')
de_post_alpha "${ASSISTANT_PATH}:streamAssist" "${FORCED_BODY}"
