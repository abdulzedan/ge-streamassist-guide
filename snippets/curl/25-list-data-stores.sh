#!/usr/bin/env bash
# ------------------------------------------------------------------
# 25 — List the data stores connected to the app.
# Feeds snippet 12 (data store grounding): shows each store's ID so
# you can restrict retrieval to specific repositories.
#
# Usage: ./25-list-data-stores.sh
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

RAW="$(de_get "${ENGINE_PATH}")"

RAW="${RAW}" python3 <<'PYEOF'
import json, os
d = json.loads(os.environ["RAW"])
if "error" in d:
    raise SystemExit("ERROR: " + d["error"]["message"])
ids = d.get("dataStoreIds", [])
print(f"{len(ids)} data stores connected to {d.get('displayName','')}:")
for i in ids:
    print(f"  {i}")
PYEOF
