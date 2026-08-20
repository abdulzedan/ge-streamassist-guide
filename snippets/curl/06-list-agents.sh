#!/usr/bin/env bash
# ------------------------------------------------------------------
# 06 — List every agent registered on the assistant.
# The agent ID printed here is what you pass in agentsSpec when
# invoking a specific agent (snippets 08-10).
#
# Usage: ./06-list-agents.sh [--raw]
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

RAW="$(de_get "${ASSISTANT_PATH}/agents?pageSize=100")"

if [[ "${1:-}" == "--raw" ]]; then
  echo "${RAW}"
  exit 0
fi

echo "${RAW}" | python3 - <<'PYEOF'
import json, sys
d = json.load(sys.stdin)
if "error" in d:
    print("ERROR:", d["error"]["message"]); sys.exit(1)
kinds = {
    "adkAgentDefinition": "high-code (ADK)",
    "a2aAgentDefinition": "high-code (A2A)",
    "managedAgentDefinition": "managed (no-code)",
    "workflowAgentDefinition": "workflow",
    "lowCodeAgentDefinition": "low-code",
    "skillAgentDefinition": "skill",
    "dialogflowAgentDefinition": "dialogflow",
}
print(f"{'AGENT_ID':22s} {'STATE':9s} {'TYPE':18s} DISPLAY NAME")
for a in d.get("agents", []):
    kind = next((v for k, v in kinds.items() if k in a), "?")
    print(f"{a['name'].split('/')[-1]:22s} {a.get('state','?'):9s} {kind:18s} {a.get('displayName','')}")
PYEOF
