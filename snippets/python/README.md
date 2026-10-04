# Python client & examples

```bash
pip install -r requirements.txt   # google-auth + requests
python examples/01_basic_streaming.py
```

[`ge_streamassist.py`](ge_streamassist.py) provides:

- `GEClient.stream_assist(...)` — generator yielding chunks as they arrive
  (true incremental decoding of the streamed JSON array),
- `GEClient.ask(...)` — collect a whole call into an `AssistResult`
  (`.text`, `.thoughts`, `.files`, `.session`, `.state`, `.skipped_reasons`,
  `.invocation_tools`, `.invoked_skills`, `.connector_auth_errors`,
  `.status_updates`, `.final_result_tool_invocation_id`),
- `upload_file`, `download_file`, `assist`, `a2a_message_send`, `a2a_message_stream`,
  `list_agents`, `list_session_files`, `list_sessions`, `delete_session`.

The A2A methods create a UUID for each message unless `message_id` is supplied.
Pass the exact Agent Registry URL as `endpoint_url` when available.

Examples (all read `../../.env` via `_env.py`):

| Example | Shows |
|---|---|
| `01_basic_streaming.py` | token-by-token output |
| `02_multi_turn.py` | session reuse |
| `03_invoke_agent.py` | list agents, invoke one |
| `04_deep_research.py` | full plan→approve→report flow |
| `05_file_qa.py` | upload + question |
| `06_generate_and_download_image.py` | image tool + download |
| `07_native_a2a.py` | direct agent messaging (no orchestrator) |
| `08_error_handling.py` | SKIPPED / mid-stream FAILED / empty answers |

Corporate machines with TLS interception: see the note in
[docs/02-authentication.md](../../docs/02-authentication.md#corporate-tls-interception).
