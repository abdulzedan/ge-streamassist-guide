"""Invoke a specific registered agent (high-code ADK/A2A or no-code).

Run with no arguments to list agents; pass an agent ID and a question
to invoke one.
"""

import sys

from _env import client

ge = client()

if len(sys.argv) < 2:
    print(f"{'AGENT_ID':22s} {'STATE':9s} DISPLAY NAME")
    for a in ge.list_agents():
        print(f"{a['name'].rsplit('/', 1)[-1]:22s} {a.get('state', '?'):9s} "
              f"{a.get('displayName', '')}")
    print(f"\nusage: python {sys.argv[0]} <agent-id> [question]")
    raise SystemExit(0)

agent_id = sys.argv[1]
question = sys.argv[2] if len(sys.argv) > 2 else "What can you help me with?"

result = ge.ask(question, session="-", agent_id=agent_id)
print("state:", result.state)
if result.skipped_reasons:
    print("skipped:", result.skipped_reasons,
          "(greetings are skipped by default; try force_assist=True)")
print(result.text)
