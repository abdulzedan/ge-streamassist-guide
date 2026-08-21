"""Demonstrates the three failure shapes you must handle.

1. SKIPPED  - chit-chat classifier (query looked non-answer-seeking)
2. FAILED   - mid-stream error chunk with HTTP 200 (e.g. inaccessible agent)
3. SUCCEEDED with empty text - legal for some managed agents
"""

from _env import client
from ge_streamassist import AssistResult

ge = client()

print("== 1. SKIPPED: greeting without skip-override ==")
r = ge.ask("hello")
print(f"   state={r.state} reasons={r.skipped_reasons} text={r.text!r}")

print("== 1b. same greeting with force_assist=True ==")
r = ge.ask("hello", force_assist=True)
print(f"   state={r.state} text={r.text.strip()[:80]!r}")

print("== 2. FAILED mid-stream: nonexistent agent + forced assist ==")
result = AssistResult()
try:
    for chunk in ge.stream_assist(query="hello", agent_id="999999999999",
                                  force_assist=True):
        result.add_chunk(chunk)  # raises on the {'error': ...} chunk
    print(f"   state={result.state} (no error chunk this time)")
except RuntimeError as exc:
    print(f"   state={result.state} then error chunk: {str(exc)[:100]}")

print("== 3. Treat empty SUCCEEDED text as a real case ==")
print("   (see docs/05-invoking-agents.md - always check result.text truthiness)")
