#!/usr/bin/env bash
# ------------------------------------------------------------------
# common.sh — shared environment for every curl snippet.
# Every snippet sources this file. It loads .env, mints an access
# token, and exports the base URLs used by the Stream Assist API.
# ------------------------------------------------------------------
set -euo pipefail

# Resolve repo root regardless of where the snippet is invoked from.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ ! -f "${REPO_ROOT}/.env" ]]; then
  echo "ERROR: ${REPO_ROOT}/.env not found. Run: cp .env.example .env  (then edit it)" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "${REPO_ROOT}/.env"

: "${PROJECT_ID:?set PROJECT_ID in .env}"
: "${LOCATION:?set LOCATION in .env}"
: "${APP_ID:?set APP_ID in .env}"
: "${ASSISTANT_ID:=default_assistant}"
: "${API_VERSION:=v1alpha}"

# Global apps use the bare hostname; regional apps (us / eu) use a
# location-prefixed hostname. Getting this wrong returns 404s.
if [[ "${LOCATION}" == "global" ]]; then
  export DE_HOST="discoveryengine.googleapis.com"
else
  export DE_HOST="${LOCATION}-discoveryengine.googleapis.com"
fi

# OAuth token from your gcloud login (user creds or service account).
TOKEN="$(gcloud auth print-access-token)"
export TOKEN

# Resource paths used throughout the API.
export ENGINE_PATH="projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/engines/${APP_ID}"
export ASSISTANT_PATH="${ENGINE_PATH}/assistants/${ASSISTANT_ID}"
export BASE_URL="https://${DE_HOST}/${API_VERSION}"

# Convenience wrapper: authenticated JSON POST.
# usage: de_post <url-after-base> <json-body>
de_post() {
  curl -sS -X POST "${BASE_URL}/$1" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -H "X-Goog-User-Project: ${PROJECT_ID}" \
    -d "$2"
}

# Convenience wrapper: authenticated GET.
# usage: de_get <url-after-base>
de_get() {
  curl -sS "${BASE_URL}/$1" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "X-Goog-User-Project: ${PROJECT_ID}"
}
