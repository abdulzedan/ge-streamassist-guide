#!/usr/bin/env bash
# ------------------------------------------------------------------
# 23 — Native A2A: fetch a registered agent's card.
# Only agents advertising an A2A interface expose this endpoint.
# The card describes its capabilities and transport.
#
# Usage: ./23-a2a-get-card.sh <agent-id>
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

AGENT_ID="${1:?usage: $0 <agent-id>   (find IDs with 06-list-agents.sh)}"
PROJECT_NUMBER="${PROJECT_NUMBER:-$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')}"
A2A_BASE="https://${DE_HOST}/v1/projects/${PROJECT_NUMBER}/locations/${LOCATION}/collections/default_collection/engines/${APP_ID}/assistants/${ASSISTANT_ID}/agents/${AGENT_ID}/a2a"

curl -sS --fail-with-body "${A2A_BASE}/v1/card" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}"
