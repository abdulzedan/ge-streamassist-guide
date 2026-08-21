#!/usr/bin/env bash
# ------------------------------------------------------------------
# 26 — Diagnose agent routing for a query.
# Sends the query with agentsSpec, then prints the orchestrator's
# plannerSteps trace: whether your agent was actually invoked
# (functionCall step), or the base assistant answered.
#
# Usage: ./26-diagnose-routing.sh <agent-id> "your question"
# Requires: jq
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

AGENT_ID="${1:?usage: $0 <agent-id> \"question\"}"
QUERY="${2:?usage: $0 <agent-id> \"question\"}"

RESP=$(de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query":   { "text": "'"${QUERY}"'" },
  "session": "'"${ENGINE_PATH}"'/sessions/-",
  "agentsSpec": { "agentSpecs": [ { "agentId": "'"${AGENT_ID}"'" } ] }
}')

echo "== final state =="
echo "${RESP}" | jq -r '.[-1].answer.state // "unknown"'
echo
echo "== planner trace =="
echo "${RESP}" | jq '[ .[] | .answer.diagnosticInfo.plannerSteps // empty ] | flatten
  | map(if .queryStep    then {step:"query", text:.queryStep.parts[0].text}
        elif .planStep   then {step:"plan",
                               call:(.planStep.parts[0].functionCall.functionName // "answer-directly")}
        elif .toolStep   then {step:"tool",
                               result:(.toolStep.parts[0].functionResult.functionName // "")}
        else . end)'
echo
CALLED=$(echo "${RESP}" | jq -r '[ .[] | .answer.diagnosticInfo.plannerSteps // empty ] | flatten
  | map(.planStep.parts[0].functionCall.functionName // empty) | first // ""')
if [[ -n "${CALLED}" ]]; then
  echo "VERDICT: routed to agent function '${CALLED}'"
else
  echo "VERDICT: NO agent functionCall found - the base assistant answered."
fi
