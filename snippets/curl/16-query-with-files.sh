#!/usr/bin/env bash
# ------------------------------------------------------------------
# 16 — Ask a question about uploaded files.
# Pass the fileId(s) from 15-upload-context-file.sh in "fileIds",
# together with the SAME session the file was uploaded to.
# fileIds is a v1alpha-only field.
#
# An empty query is allowed when fileIds are present — the assistant
# then answers based on the files alone.
#
# Usage: ./16-query-with-files.sh <session-id> <file-id> "question"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

SESSION_ID="${1:?usage: $0 <session-id> <file-id> \"question\"}"
FILE_ID="${2:?usage: $0 <session-id> <file-id> \"question\"}"
QUERY="${3:-Summarize the attached file.}"

de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query":   { "text": "'"${QUERY}"'" },
  "session": "'"${ENGINE_PATH}"'/sessions/'"${SESSION_ID}"'",
  "fileIds": [ "'"${FILE_ID}"'" ]
}'
