#!/usr/bin/env bash
# ------------------------------------------------------------------
# 22 — Inspect the assistant's configuration.
# Shows webGroundingType (whether snippet 11 will work), enabled
# tools, generation config, and customer policy (banned phrases /
# Model Armor) — useful when a call is skipped or a tool silently
# does nothing.
#
# Usage: ./22-get-assistant.sh
# ------------------------------------------------------------------
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

de_get "${ASSISTANT_PATH}"
