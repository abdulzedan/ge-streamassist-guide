"""Deep Research end-to-end: plan -> approve -> stream the report.

The research phase commonly runs 5-20 minutes; progress markers are
printed as contentKind transitions (RESEARCH_QUESTION / RESEARCH_ANSWER).
Requires the deep_research agent (API access is allowlisted).
"""

import sys

from _env import client

TOPIC = sys.argv[1] if len(sys.argv) > 1 else (
    "Current trends in agentic AI adoption in retail banking")

ge = client()

print(f"== Step 1: research plan for: {TOPIC}")
plan = ge.ask(TOPIC, session="-", agent_id="deep_research",
              tools_spec={"webGroundingSpec": {}})
print(plan.text[:2000])
print("\n== Step 2: approving plan; streaming research (be patient)…\n")

last_kind = None
text_len = 0
for chunk in ge.stream_assist(query="Start Research", session=plan.session,
                              agent_id="deep_research",
                              tools_spec={"webGroundingSpec": {}}):
    for reply in (chunk.get("answer") or {}).get("replies", []):
        gc = reply.get("groundedContent") or {}
        kind = (gc.get("contentMetadata") or {}).get("contentKind")
        if kind and kind != last_kind:
            print(f"\n--- [{kind}] ---")
            last_kind = kind
        content = gc.get("content") or {}
        if content.get("text") and not content.get("thought"):
            print(content["text"], end="", flush=True)
            text_len += len(content["text"])
        if "file" in content:
            print(f"\n[file reply: {content['file']}]")
print(f"\n\ndone; total report characters: {text_len}")
