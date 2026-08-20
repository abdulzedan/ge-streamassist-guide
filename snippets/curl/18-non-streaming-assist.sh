#!/usr/bin/env bash
# ------------------------------------------------------------------
# 18 — Non-streaming :assist.
# Same request shape as streamAssist, but the response is a single
# JSON object containing the complete answer — easier to consume
# from tools that can't handle streams.
#
# CAVEAT: :assist is NOT in the public API reference (streamAssist
# is the documented surface). It works today on v1alpha, but treat
# it as best-effort; prefer streamAssist for production.
#
# Usage: ./18-non-streaming-assist.sh "your question"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

QUERY="${1:-Summarize what this assistant can do in one paragraph.}"

de_post "${ASSISTANT_PATH}:assist" '{
  "query": { "text": "'"${QUERY}"'" }
}'
