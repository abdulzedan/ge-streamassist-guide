# 12. Production notes

## requests

- Default to `v1`; use `v1alpha` only for the alpha fields or control-plane calls you need.
- StreamAssist supports Core Assistant, Deep Research and Agent Designer chat agents. Use registry A2A for registered ADK/A2A agents.
- Workflow agents remain unsupported through StreamAssist even though the REST schema contains workflow-related fields.
- A registry entry must advertise `A2A_AGENT`. Card and message calls fail for agents without it.
- A2A agent registration and file-based Q&A are Preview.
- StreamAssist does not support mutative connector actions.
- Data-store and registry A2A paths use the project number.
- Build JSON with a serializer. Shell string interpolation breaks on quotes, backslashes and newlines.

## responses

- Stream responses are JSON arrays, not SSE or NDJSON.
- Inspect every object: errors can arrive after HTTP 200.
- On `v1`, read `sessionInfo` from the final response object.
- Keep `thought: true` content out of the displayed answer.
- `SUCCEEDED` can have no text. Native A2A may return an auth or confirmation handoff instead.
- Planner diagnostics are optional; missing `functionCall` is not proof of failed routing.
- Check `invocationTools`, `invokedSkills` and `connectorAuthErrors`; a connector can fail authentication while the answer still succeeds.

## sessions and files

- Reuse the same session for multiple turns and attached files.
- `listSessionFileMetadata` and `fileIds` are `v1alpha`; upload and download work on `v1`.
- Use `alt=media` and follow redirects when downloading.
- API sessions can appear in the caller's UI history. Use `isSessionLess` for disposable alpha calls.
- Caller identity controls ACL-aware grounding and personalization.

## operations

- Send `X-Goog-User-Project` with ADC or user credentials.
- Size timeouts for quiet research and media streams.
- Keep `assistToken` for support. Never store bearer tokens or OAuth authorization URLs.
- Treat the Usage & Spending page as the quota source of truth. A 429 alone does not identify which limit was hit.
- Check the billing model before applying seat-based quota math. Pay-as-you-go and seat plans use different rules.
- The 99.5% StreamAssist SLA excludes pre-GA features and calls involving built-in, user-defined or external runtime agents.
