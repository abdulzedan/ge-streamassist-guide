#!/usr/bin/env bash
# ------------------------------------------------------------------
# 12 — Ground the answer on a SPECIFIC data store.
# By default the assistant may search all connected data stores.
# vertexAiSearchSpec.dataStoreSpecs restricts retrieval to the ones
# you list (only meaningful on apps with multiple data stores).
#
# The data-store path requires the project number. This snippet
# resolves it instead of reusing PROJECT_ID.
#
# Optional per-store extras (see docs/06-tools.md):
#   "filter": "category: ANY(\"reports\")"   — metadata filter
#   "boostSpec": {...}                        — boost/bury documents
#
# Usage: ./12-datastore-grounding.sh <data-store-id> "your question"
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

DATA_STORE_ID="${1:?usage: $0 <data-store-id> \"question\"}"
QUERY="${2:?usage: $0 <data-store-id> \"question\"}"

PROJECT_NUMBER="${PROJECT_NUMBER:-$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')}"

DATA_STORE="projects/${PROJECT_NUMBER}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}"
BODY=$(jq -nc --arg query "${QUERY}" --arg store "${DATA_STORE}" \
  '{query: {text: $query}, toolsSpec: {vertexAiSearchSpec: {dataStoreSpecs: [{dataStore: $store}]}}}')
de_post "${ASSISTANT_PATH}:streamAssist" "${BODY}"
