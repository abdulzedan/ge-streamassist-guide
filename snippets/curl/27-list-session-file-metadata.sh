#!/usr/bin/env bash
# ------------------------------------------------------------------
# 27 — List a session's context files (the way that actually works).
# Use :listSessionFileMetadata (AssistantService). Do NOT use
# :listFiles — that verb belongs to an unreleased collaborative-
# projects surface and returns a misleading 403
# ("Session is not owned by the provided user") for API-created
# sessions. :listSessionFileMetadata works headless with the same
# credentials that created the session.
#
# Usage: ./27-list-session-file-metadata.sh <session-id>
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

SESSION_ID="${1:?usage: $0 <session-id>}"

de_get "${ENGINE_PATH}/sessions/${SESSION_ID}:listSessionFileMetadata"
