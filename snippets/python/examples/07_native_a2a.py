"""Message an agent directly over the native A2A surface (no orchestrator).

Guarantees the agent receives the message — no routing heuristics and no
chit-chat classifier in between.
"""

import sys

from _env import client

if len(sys.argv) < 2:
    raise SystemExit(f"usage: python {sys.argv[0]} <agent-id> [message]")

agent_id = sys.argv[1]
text = sys.argv[2] if len(sys.argv) > 2 else "Briefly, what do you do?"

ge = client()
context_id = None
for item in ge.a2a_message_stream(agent_id, text):
    msg = item.get("message") or {}
    context_id = msg.get("contextId") or context_id
    answer = (msg.get("metadata") or {}).get("answer") or {}
    for reply in answer.get("replies", []):
        content = (reply.get("groundedContent") or {}).get("content") or {}
        if content.get("text") and not content.get("thought"):
            print(content["text"], end="", flush=True)
print(f"\n\ncontextId (reuse for multi-turn): {context_id}")
