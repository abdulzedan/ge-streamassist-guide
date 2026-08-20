#!/usr/bin/env bash
# ------------------------------------------------------------------
# 20 — Language hints and user metadata.
# userMetadata.preferredLanguageCode is a FALLBACK used when
# language detection on the query fails — it does not force the
# output language (write the query in the target language, or say
# "answer in French", if you need a guaranteed language).
# timeZone makes time-relative answers ("this quarter") correct.
#
# Usage: ./20-language-and-user-metadata.sh
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

de_post "${ASSISTANT_PATH}:streamAssist" '{
  "query": { "text": "Quels sont les avantages des achats périodiques par sommes fixes?" },
  "userMetadata": {
    "preferredLanguageCode": "fr-CA",
    "timeZone": "America/Toronto"
  }
}'
