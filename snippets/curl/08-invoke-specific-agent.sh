#!/usr/bin/env bash
# ------------------------------------------------------------------
# 08 — Invoke a SPECIFIC agent (high-code ADK, A2A, or no-code).
# The agentsSpec pins the call to one agent. Without it the
# orchestrator picks whatever it wants — usually the base assistant —
# which is the #1 source of "my agent isn't being called" bugs.
#
# Works the same for every agent type; only the agent ID differs.
#
# Usage: ./08-invoke-specific-agent.sh <agent-id> "your question"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

AGENT_ID="${1:?usage: $0 <agent-id> \"question\"   (find IDs with 06-list-agents.sh)}"
QUERY="${2:?usage: $0 <agent-id> \"question\"}"

de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query":   { "text": "'"${QUERY}"'" },
  "session": "'"${ENGINE_PATH}"'/sessions/-",
  "agentsSpec": {
    "agentSpecs": [ { "agentId": "'"${AGENT_ID}"'" } ]
  }
}'
