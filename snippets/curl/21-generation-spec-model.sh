#!/usr/bin/env bash
# ------------------------------------------------------------------
# 21 — Override the answer model for one request.
# generationSpec.modelId overrides the engine-level default model
# for this call only. Available model IDs depend on your edition
# and allowlists; an invalid ID fails the request.
#
# Usage: ./21-generation-spec-model.sh <model-id> "question"
# Example: ./21-generation-spec-model.sh gemini-2.5-flash "Say OK."
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

MODEL_ID="${1:-gemini-2.5-flash}"
QUERY="${2:-Say OK.}"

de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query": { "text": "'"${QUERY}"'" },
  "generationSpec": { "modelId": "'"${MODEL_ID}"'" }
}'
