"""Multi-turn conversation: reuse the session returned by turn 1."""

from _env import client

ge = client()

turn1 = ge.ask("My name is Jordan and I work in fixed income. Remember that.",
               session="-")
print("turn 1:", turn1.text.strip()[:200])
print("session:", turn1.session_id)

turn2 = ge.ask("What is my name and what asset class do I work in?",
               session=turn1.session)
print("turn 2:", turn2.text.strip())
