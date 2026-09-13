#!/usr/bin/env bash
# ------------------------------------------------------------------
# 27 — List a session's context files. This method is v1alpha.
#
# Usage: ./27-list-session-file-metadata.sh <session-id>
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

SESSION_ID="${1:?usage: $0 <session-id>}"

de_get_alpha "${ENGINE_PATH}/sessions/${SESSION_ID}:listSessionFileMetadata"
