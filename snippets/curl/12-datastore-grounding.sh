#!/usr/bin/env bash
# ------------------------------------------------------------------
# 12 — Ground the answer on a SPECIFIC data store.
# By default the assistant may search all connected data stores.
# vertexAiSearchSpec.dataStoreSpecs restricts retrieval to the ones
# you list (only meaningful on apps with multiple data stores).
#
# GOTCHA: per the API reference this field requires the PROJECT
# NUMBER (project ID "not supported"). Project ID has been observed
# to work, but don't rely on it — this snippet resolves the number.
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

PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')

de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query": { "text": "'"${QUERY}"'" },
  "toolsSpec": {
    "vertexAiSearchSpec": {
      "dataStoreSpecs": [
        { "dataStore": "projects/'"${PROJECT_NUMBER}"'/locations/'"${LOCATION}"'/collections/default_collection/dataStores/'"${DATA_STORE_ID}"'" }
      ]
    }
  }
}'
