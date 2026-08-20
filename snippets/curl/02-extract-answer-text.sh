#!/usr/bin/env bash
# ------------------------------------------------------------------
# 02 — streamAssist + extract just the answer text.
# Same call as 01, piped through jq to concatenate the text of every
# reply fragment while dropping "thought" fragments and metadata.
#
# Usage: ./02-extract-answer-text.sh "your question"
# Requires: jq
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

QUERY="${1:-Summarize what dollar-cost averaging is in two sentences.}"

de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query": { "text": "'"${QUERY}"'" }
}' | jq -r '
  [ .[]
    | .answer.replies[]?
    | .groundedContent.content
    | select(. != null and .thought != true)
    | .text // empty
  ] | join("")'
