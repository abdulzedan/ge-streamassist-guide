#!/usr/bin/env bash
# ------------------------------------------------------------------
# 23 — Native A2A: fetch a registered agent's card.
# Every agent registered on the assistant exposes an A2A endpoint;
# the card describes its capabilities and transport. This surface is
# v1 (not v1alpha).
#
# Usage: ./23-a2a-get-card.sh <agent-id>
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

AGENT_ID="${1:?usage: $0 <agent-id>   (find IDs with 06-list-agents.sh)}"

curl -sS "https://${DE_HOST}/v1/${ASSISTANT_PATH}/agents/${AGENT_ID}/a2a/v1/card" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}"
