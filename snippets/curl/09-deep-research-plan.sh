#!/usr/bin/env bash
# ------------------------------------------------------------------
# 09 — Deep Research, step 1 of 2: request the research plan.
# Deep Research is a two-step flow:
#   step 1: send the topic  -> agent returns a RESEARCH PLAN
#   step 2 (snippet 10): approve in the SAME session -> full report
#
# Note: Deep Research via API is GA **with allowlist**, and Made by
# Google agents are not available in Frontline edition.
#
# Usage: ./09-deep-research-plan.sh "research topic"
# Requires: jq
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

TOPIC="${1:-Current trends in agentic AI adoption in retail banking}"

BODY=$(jq -nc --arg topic "${TOPIC}" --arg session "${ENGINE_PATH}/sessions/-" \
  '{query: {text: $topic}, session: $session,
    agentsSpec: {agentSpecs: [{agentId: "deep_research"}]},
    toolsSpec: {webGroundingSpec: {}}}')
RESP=$(de_post "${ASSISTANT_PATH}:streamAssist" "${BODY}")

echo "== Research plan =="
echo "${RESP}" | jq -r '[ .[] | .answer.replies[]? | .groundedContent.content
                          | select(. != null and .thought != true) | .text // empty ] | join("")'
SESSION=$(echo "${RESP}" | jq -er '[.[] | .sessionInfo.session // empty] | last')
echo
echo "== session: ${SESSION}"
echo
echo "== To execute the plan, run: =="
echo "./10-deep-research-execute.sh ${SESSION##*/}"
