#!/usr/bin/env bash
# ------------------------------------------------------------------
# 07 — Get one agent's full definition.
# Shows which type it is (adkAgentDefinition / a2aAgentDefinition /
# managedAgentDefinition / ...), its state, authorization config and
# — for ADK agents — the backing Reasoning Engine resource.
#
# Usage: ./07-get-agent.sh <agent-id>
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

AGENT_ID="${1:?usage: $0 <agent-id>   (find IDs with 06-list-agents.sh)}"

de_get "${ASSISTANT_PATH}/agents/${AGENT_ID}"
