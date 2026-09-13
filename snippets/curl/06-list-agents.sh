#!/usr/bin/env bash
# ------------------------------------------------------------------
# 06 — List every agent registered on the assistant.
# Agent discovery is v1alpha. Check the type before choosing the
# Stream Assist or native A2A invocation path.
#
# Usage: ./06-list-agents.sh [--raw]
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

RAW="$(de_get_alpha "${ASSISTANT_PATH}/agents?pageSize=100")"

if [[ "${1:-}" == "--raw" ]]; then
  echo "${RAW}"
  exit 0
fi

RAW="${RAW}" python3 <<'PYEOF'
import json, os, sys
d = json.loads(os.environ["RAW"])
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
