# Captured outputs

Real responses captured while executing the snippets against a live Gemini
Enterprise app, so you can see the exact shape of what comes back before
running anything yourself.

Sanitization applied: project numbers → `000000000000`, project ID →
`your-project-id`, `assistToken` values → `REDACTED_ASSIST_TOKEN`. Structure,
field names, states and text content are untouched. Files named `*.excerpt.*`
are truncated (the deep-research execution response alone is ~1.8 MB).

| File | Produced by |
|---|---|
| `01-basic-stream-assist.json` | curl 01 |
| `04-multi-turn-session.json` | curl 04 (turn 2 — note the recalled facts) |
| `08-invoke-adk-agent.excerpt.json` | curl 08 vs an ADK agent |
| `08-invoke-a2a-agent.excerpt.json` | curl 08 vs an A2A agent |
| `09-deep-research-plan.json` | curl 09 |
| `10-deep-research-execute.excerpt.json` | curl 10 (contentKind markers) |
| `11-web-grounding.excerpt.json` | curl 11 (grounding metadata) |
| `13-image-generation.json` | curl 13 (file reply) |
| `14-video-generation.json` | curl 14 (file reply) |
| `15-add-context-file.json` | curl 15 |
| `16-query-with-files.json` | curl 16 |
| `18-non-streaming-assist.json` | curl 18 |
| `19-skipped-chitchat.json` | curl 19 (default half) |
| `20-language-user-metadata.json` | curl 20 |
| `24-a2a-message-stream.excerpt.json` | curl 24 (native A2A) |
