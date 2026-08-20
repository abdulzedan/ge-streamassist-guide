#!/usr/bin/env bash
# ------------------------------------------------------------------
# 15 — Upload a file into a session (addContextFile).
# This is the documented way to attach a file: base64 the content
# into a JSON body. Passing "-" as the session ID creates a new
# session and uploads in one call.
#
# The response contains the session name and the fileId — pass the
# fileId to streamAssist via "fileIds" (snippet 16).
#
# Preview/pre-GA feature. Practical size ceiling: base64 in a JSON
# body — use it for documents, not gigabyte archives (see
# docs/08-files.md for the multipart alternative).
#
# Usage: ./15-upload-context-file.sh <path-to-file> [session-id]
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

FILE_PATH="${1:?usage: $0 <path-to-file> [session-id]}"
SESSION_ID="${2:--}"   # "-" = create a new session

FILE_NAME="$(basename "${FILE_PATH}")"
MIME_TYPE="$(file --mime-type -b "${FILE_PATH}")"
# -i keeps macOS/BSD base64 happy; GNU base64 users can use -w 0.
BASE64_CONTENT="$(base64 -i "${FILE_PATH}" | tr -d '\n')"

de_post "${ENGINE_PATH}/sessions/${SESSION_ID}:addContextFile" '{
  "fileName":     "'"${FILE_NAME}"'",
  "mimeType":     "'"${MIME_TYPE}"'",
  "fileContents": "'"${BASE64_CONTENT}"'"
}'
