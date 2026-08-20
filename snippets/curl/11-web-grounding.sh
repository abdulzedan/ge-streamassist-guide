#!/usr/bin/env bash
# ------------------------------------------------------------------
# 11 — Ground the answer with web search.
# webGroundingSpec is an EMPTY object — its mere presence enables
# web grounding. Only works if the assistant's webGroundingType is
# WEB_GROUNDING_TYPE_GOOGLE_SEARCH or _ENTERPRISE_WEB_SEARCH
# (check with: 22-get-assistant.sh).
#
# Usage: ./11-web-grounding.sh "a question about current events"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

QUERY="${1:-What was the most recent US Fed funds rate decision?}"

de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query": { "text": "'"${QUERY}"'" },
  "toolsSpec": { "webGroundingSpec": {} }
}'
