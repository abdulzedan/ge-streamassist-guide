"""Generate an image and download the PNG from the session's context files."""

import sys

from _env import client

PROMPT = sys.argv[1] if len(sys.argv) > 1 else (
    "A simple bar chart concept: three ascending blue bars on white.")

ge = client()

result = ge.ask(f"Generate an image: {PROMPT}", session="-",
                tools_spec={"imageGenerationSpec": {}})
print("state:", result.state, "| text:", result.text.strip()[:120])

if not result.files:
    raise SystemExit("No file reply — is image generation enabled for this app?")

out = ge.download_file(result.session_id, result.files[0]["fileId"], "generated.png")
print("saved:", out, f"({result.files[0]['mimeType']})")
