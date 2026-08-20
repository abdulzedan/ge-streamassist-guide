#!/usr/bin/env bash
# ------------------------------------------------------------------
# discover.sh — find your Gemini Enterprise app and agents.
# Run this first: it verifies auth and prints the values you need
# for .env (PROJECT_ID / LOCATION / APP_ID) plus every registered
# agent with its ID, type, and state.
#
# Usage:
#   ./scripts/discover.sh <project-id> [location]   # location: global|us|eu
#   ./scripts/discover.sh                            # uses .env if present
# ------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PROJECT_ID="${1:-}"
LOCATION="${2:-global}"

if [[ -z "${PROJECT_ID}" && -f "${REPO_ROOT}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
fi
: "${PROJECT_ID:?usage: ./scripts/discover.sh <project-id> [location]}"

if [[ "${LOCATION}" == "global" ]]; then
  DE_HOST="discoveryengine.googleapis.com"
else
  DE_HOST="${LOCATION}-discoveryengine.googleapis.com"
fi

TOKEN="$(gcloud auth print-access-token)"
BASE="https://${DE_HOST}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection"

echo "== Engines (Gemini Enterprise apps) in ${PROJECT_ID}/${LOCATION} =="
curl -sS "${BASE}/engines" \
  -H "Authorization: Bearer ${TOKEN}" -H "X-Goog-User-Project: ${PROJECT_ID}" \
  | python3 -c '
import json, sys
d = json.load(sys.stdin)
if "error" in d:
    print("ERROR:", d["error"]["message"]); sys.exit(1)
for e in d.get("engines", []):
    print(f'"'"'  APP_ID={e["name"].split("/")[-1]}  ({e.get("displayName","")})'"'"')
'

echo
echo "== Registered agents per app =="
for ENGINE in $(curl -sS "${BASE}/engines" \
    -H "Authorization: Bearer ${TOKEN}" -H "X-Goog-User-Project: ${PROJECT_ID}" \
    | python3 -c 'import json,sys; [print(e["name"].split("/")[-1]) for e in json.load(sys.stdin).get("engines",[])]'); do
  echo "-- ${ENGINE}"
  curl -sS "${BASE}/engines/${ENGINE}/assistants/default_assistant/agents?pageSize=100" \
    -H "Authorization: Bearer ${TOKEN}" -H "X-Goog-User-Project: ${PROJECT_ID}" \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
if "error" in d:
    print("   (no assistant or no access:", d["error"]["status"] + ")"); sys.exit(0)
kinds = {
    "adkAgentDefinition": "high-code (ADK on Agent Engine)",
    "a2aAgentDefinition": "high-code (A2A endpoint)",
    "managedAgentDefinition": "Google-managed (no-code)",
    "workflowAgentDefinition": "workflow (no-code)",
    "lowCodeAgentDefinition": "low-code (Agent Designer)",
    "skillAgentDefinition": "skill",
    "dialogflowAgentDefinition": "Dialogflow CX",
}
for a in d.get("agents", []):
    kind = next((v for k, v in kinds.items() if k in a), "unknown")
    print(f'"'"'   {a["name"].split("/")[-1]:22s} {a.get("state","?"):9s} {kind:32s} {a.get("displayName","")}'"'"')
'
done
