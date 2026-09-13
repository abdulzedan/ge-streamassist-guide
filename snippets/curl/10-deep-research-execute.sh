#!/usr/bin/env bash
# ------------------------------------------------------------------
# 10 — Deep Research, step 2 of 2: approve the plan and run it.
# Must reuse the session from step 1 (snippet 09) and pin
# deep_research again via agentsSpec. The stream stays open for the
# whole run — often several minutes — and emits contentMetadata
# contentKind markers: RESEARCH_PLAN, RESEARCH_QUESTION,
# RESEARCH_ANSWER, RESEARCH_AUDIO_SUMMARY.
#
# The final report text arrives as RESEARCH_ANSWER fragments; an
# audio summary (if produced) arrives as a file reply you can fetch
# with 17-download-session-file.sh.
#
# Usage: ./10-deep-research-execute.sh <session-id>
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

SESSION_ID="${1:?usage: $0 <session-id>   (printed by 09-deep-research-plan.sh)}"

# Long-running: raise curl's default timeouts.
BODY=$(jq -nc --arg session "${ENGINE_PATH}/sessions/${SESSION_ID}" \
  '{query: {text: "Start Research"}, session: $session,
    agentsSpec: {agentSpecs: [{agentId: "deep_research"}]},
    toolsSpec: {webGroundingSpec: {}}}')

curl -sS --fail-with-body --max-time 1800 -X POST "${BASE_URL}/${ASSISTANT_PATH}:streamAssist" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d "${BODY}"
