"""Stream an answer token-by-token to stdout."""

from _env import client

ge = client()

for chunk in ge.stream_assist(query="Explain dollar-cost averaging in three sentences."):
    for reply in (chunk.get("answer") or {}).get("replies", []):
        content = (reply.get("groundedContent") or {}).get("content") or {}
        if content.get("text") and not content.get("thought"):
            print(content["text"], end="", flush=True)
print()
