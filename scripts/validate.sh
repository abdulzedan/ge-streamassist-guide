#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
[[ -x .venv/bin/python ]] && PYTHON_BIN=.venv/bin/python

while IFS= read -r file; do bash -n "${file}"; done < <(find . -name '*.sh' -type f | sort)
PYTHONPYCACHEPREFIX="$(mktemp -d)/pycache" "${PYTHON_BIN}" -m compileall -q scripts snippets/python soak/soak tests
node --check snippets/node/ge-streamassist.mjs
node --check snippets/node/example.mjs
node --test tests/test_node.mjs
"${PYTHON_BIN}" -m unittest discover -s tests -v
"${PYTHON_BIN}" scripts/check-links.py

while IFS= read -r file; do jq -e . "${file}" >/dev/null; done \
  < <(find outputs -name '*.json' ! -name '*.excerpt.json' -type f | sort)

echo "repository checks: ok"
