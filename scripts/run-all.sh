#!/usr/bin/env bash
# ------------------------------------------------------------------
# run-all.sh — smoke-test the whole snippet suite against your app.
# Runs every fast, side-effect-light snippet and prints PASS/FAIL.
# (Deep Research execution and video generation are excluded by
# default because they are slow; pass --full to include them.)
#
# Usage: ./scripts/run-all.sh [--full]
# ------------------------------------------------------------------
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURL_DIR="${REPO_ROOT}/snippets/curl"
FULL="${1:-}"

pass=0; fail=0
run() {
  local name="$1"; shift
  printf '%-46s' "${name}"
  if out=$("$@" 2>&1); then
    if echo "${out}" | grep -q '"error"'; then
      echo "FAIL (error in response)"; echo "${out}" | head -5; fail=$((fail+1))
    else
      echo "PASS"; pass=$((pass+1))
    fi
  else
    echo "FAIL (exit $?)"; echo "${out}" | head -5; fail=$((fail+1))
  fi
}

run "01 basic streamAssist"        "${CURL_DIR}/01-basic-stream-assist.sh" "Say OK."
run "02 extract answer text"       "${CURL_DIR}/02-extract-answer-text.sh" "Say OK."
run "03 create session"            "${CURL_DIR}/03-create-session.sh" "smoke-test"
run "04 multi-turn session"        "${CURL_DIR}/04-multi-turn-session.sh"
run "05 list sessions"             "${CURL_DIR}/05-session-crud.sh" list
run "06 list agents"               "${CURL_DIR}/06-list-agents.sh"
run "11 web grounding"             "${CURL_DIR}/11-web-grounding.sh" "What day is it today?"
run "18 non-streaming assist"      "${CURL_DIR}/18-non-streaming-assist.sh" "Say OK."
run "19 assist skipping mode"      "${CURL_DIR}/19-assist-skipping-mode.sh" "hello"
run "20 language and metadata"     "${CURL_DIR}/20-language-and-user-metadata.sh"
run "22 get assistant"             "${CURL_DIR}/22-get-assistant.sh"

# File round trip: upload -> query -> download uses a temp memo.
TMPFILE=$(mktemp /tmp/ge-smoke-XXXX.txt)
echo "Smoke test memo. The magic number is 42." > "${TMPFILE}"
printf '%-46s' "15+16 file upload + query"
UP=$("${CURL_DIR}/15-upload-context-file.sh" "${TMPFILE}" 2>&1)
SID=$(echo "${UP}" | python3 -c "import json,sys;print(json.load(sys.stdin)['session'].rsplit('/',1)[-1])" 2>/dev/null)
FID=$(echo "${UP}" | python3 -c "import json,sys;print(json.load(sys.stdin)['fileId'])" 2>/dev/null)
if [[ -n "${SID}" && -n "${FID}" ]] && "${CURL_DIR}/16-query-with-files.sh" "${SID}" "${FID}" "What is the magic number?" | grep -q "42"; then
  echo "PASS"; pass=$((pass+1))
else
  echo "FAIL"; fail=$((fail+1))
fi
rm -f "${TMPFILE}"

if [[ "${FULL}" == "--full" ]]; then
  run "09 deep research plan"      "${CURL_DIR}/09-deep-research-plan.sh" "Trends in retail banking AI"
  run "13 image generation"        "${CURL_DIR}/13-image-generation.sh" "a blue circle"
  run "14 video generation"        "${CURL_DIR}/14-video-generation.sh" "a calm ocean"
fi

echo
echo "passed: ${pass}  failed: ${fail}"
exit $((fail > 0))
