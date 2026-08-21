#!/usr/bin/env bash
# ------------------------------------------------------------------
# setup-env.sh — one-command bootstrap.
# Verifies gcloud auth, lets you pick a project + app, and writes
# .env ready for every snippet in the repo.
#
# Usage: ./scripts/setup-env.sh <project-id> [location]
# ------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ID="${1:?usage: $0 <project-id> [location]}"
LOCATION="${2:-global}"

if ! gcloud auth print-access-token >/dev/null 2>&1; then
  echo "ERROR: gcloud has no active credentials. Run: gcloud auth login" >&2
  exit 1
fi

if [[ "${LOCATION}" == "global" ]]; then
  DE_HOST="discoveryengine.googleapis.com"
else
  DE_HOST="${LOCATION}-discoveryengine.googleapis.com"
fi

TOKEN="$(gcloud auth print-access-token)"
ENGINES_JSON=$(curl -sS "https://${DE_HOST}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/engines" \
  -H "Authorization: Bearer ${TOKEN}" -H "X-Goog-User-Project: ${PROJECT_ID}")

# bash-3.2 compatible (macOS default shell has no mapfile)
APP_IDS=()
while IFS= read -r line; do APP_IDS+=("$line"); done < <(ENGINES_JSON="${ENGINES_JSON}" python3 <<'PYEOF'
import json, os, sys
d = json.loads(os.environ["ENGINES_JSON"])
if "error" in d:
    sys.exit("ERROR: " + d["error"]["message"])
engines = d.get("engines", [])
if not engines:
    sys.exit("ERROR: no Gemini Enterprise apps found in this project/location.")
for e in engines:
    print(e["name"].rsplit("/", 1)[-1] + "\t" + e.get("displayName", ""))
PYEOF
)

if [[ ${#APP_IDS[@]} -eq 1 ]]; then
  APP_ID="${APP_IDS[0]%%$'\t'*}"
else
  echo "Multiple apps found:"
  for i in "${!APP_IDS[@]}"; do
    echo "  $((i + 1)). ${APP_IDS[$i]%%$'\t'*}  (${APP_IDS[$i]#*$'\t'})"
  done
  read -r -p "Pick a number: " choice
  APP_ID="${APP_IDS[$((choice - 1))]%%$'\t'*}"
fi

cat > "${REPO_ROOT}/.env" <<EOF
export PROJECT_ID="${PROJECT_ID}"
export LOCATION="${LOCATION}"
export APP_ID="${APP_ID}"
export ASSISTANT_ID="default_assistant"
export API_VERSION="v1alpha"
EOF

echo "Wrote ${REPO_ROOT}/.env:"
cat "${REPO_ROOT}/.env"
echo
echo "Try it: ./snippets/curl/01-basic-stream-assist.sh \"What can you do?\""
