#!/usr/bin/env bash
# ------------------------------------------------------------------
# 18 — Non-streaming :assist.
# Returns one JSON object containing the complete answer. Its request
# supports query, session, assistSkippingMode, fileIds and userMetadata.
#
# Usage: ./18-non-streaming-assist.sh "your question"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

QUERY="${1:-Summarize what this assistant can do in one paragraph.}"

BODY=$(jq -nc --arg query "${QUERY}" '{query: {text: $query}}')
de_post "${ASSISTANT_PATH}:assist" "${BODY}"
