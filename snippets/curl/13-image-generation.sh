#!/usr/bin/env bash
# ------------------------------------------------------------------
# 13 — Generate an image.
# imageGenerationSpec is an empty object; presence enables the tool.
# The image does NOT come back inline — the reply contains a
# content.file with a fileId + mimeType (image/png). Download it
# from the session with 17-download-session-file.sh.
#
# Usage: ./13-image-generation.sh "image prompt"
# Requires: jq
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

PROMPT="${1:-A simple bar chart concept: three ascending blue bars on a white background.}"

RESP=$(de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query": { "text": "Generate an image: '"${PROMPT}"'" },
  "session": "'"${ENGINE_PATH}"'/sessions/-",
  "toolsSpec": { "imageGenerationSpec": {} }
}')

echo "${RESP}" | jq '[ .[] | .answer.replies[]? | .groundedContent.content | select(. != null) ]'
echo
SESSION_ID=$(echo "${RESP}" | jq -r '[.[] | .sessionInfo.session // empty][0]' | awk -F/ '{print $NF}')
FILE_ID=$(echo "${RESP}" | jq -r '[ .[] | .answer.replies[]? | .groundedContent.content.file.fileId // empty ][0]')
echo "Download it with:"
echo "  ./17-download-session-file.sh ${SESSION_ID} ${FILE_ID} image.png"
