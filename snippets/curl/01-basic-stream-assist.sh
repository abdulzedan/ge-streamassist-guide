#!/usr/bin/env bash
# ------------------------------------------------------------------
# 01 — Basic streamAssist call.
# The simplest possible request: a text query, no session, no agent.
# The response is a STREAMED JSON ARRAY of StreamAssistResponse
# chunks (not SSE, not NDJSON — see docs/09-parsing-the-stream.md).
#
# Usage: ./01-basic-stream-assist.sh "your question"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

QUERY="${1:-What can this assistant do?}"

de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query": { "text": "'"${QUERY}"'" }
}'
