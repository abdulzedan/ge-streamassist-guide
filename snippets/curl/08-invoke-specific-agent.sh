#!/usr/bin/env bash
# ------------------------------------------------------------------
# 08 — Invoke a Stream Assist-supported agent directly.
# Supported types: Core Assistant, Deep Research and Agent Designer
# chat agents. Registered ADK/A2A agents use snippet 24 instead.
#
# Usage: ./08-invoke-specific-agent.sh <agent-id> "your question"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

AGENT_ID="${1:?usage: $0 <agent-id> \"question\"   (find IDs with 06-list-agents.sh)}"
QUERY="${2:?usage: $0 <agent-id> \"question\"}"

BODY=$(jq -nc --arg query "${QUERY}" --arg session "${ENGINE_PATH}/sessions/-" \
  --arg agent "${AGENT_ID}" \
  '{query: {text: $query}, session: $session, agentsSpec: {agentSpecs: [{agentId: $agent}]}}')
de_post "${ASSISTANT_PATH}:streamAssist" "${BODY}"
