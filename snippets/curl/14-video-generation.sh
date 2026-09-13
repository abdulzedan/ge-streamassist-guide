#!/usr/bin/env bash
# ------------------------------------------------------------------
# 14 — Generate a video.
# Same pattern as image generation: videoGenerationSpec is an empty
# object, and the result is a content.file reply (video/mp4) whose
# fileId you download from the session afterwards.
# Video generation can take a minute or more — timeout is raised.
#
# Usage: ./14-video-generation.sh "video prompt"
# Requires: jq
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

PROMPT="${1:-A calm ocean at sunrise, gentle waves.}"

BODY=$(jq -nc --arg prompt "Generate a video: ${PROMPT}" --arg session "${ENGINE_PATH}/sessions/-" \
  '{query: {text: $prompt}, session: $session, toolsSpec: {videoGenerationSpec: {}}}')

RESP=$(curl -sS --fail-with-body --max-time 600 -X POST "${BASE_URL}/${ASSISTANT_PATH}:streamAssist" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d "${BODY}")

echo "${RESP}" | jq '[ .[] | .answer.replies[]? | .groundedContent.content | select(. != null) ]'
echo
SESSION_ID=$(echo "${RESP}" | jq -er '[.[] | .sessionInfo.session // empty] | last' | awk -F/ '{print $NF}')
FILE_ID=$(echo "${RESP}" | jq -r '[ .[] | .answer.replies[]? | .groundedContent.content.file.fileId // empty ][0]')
echo "session: ${SESSION_ID}"
echo "Download it with:"
echo "  ./17-download-session-file.sh ${SESSION_ID} ${FILE_ID} video.mp4"
