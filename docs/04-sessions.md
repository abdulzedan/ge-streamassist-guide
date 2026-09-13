# 4. Sessions

A session stores the turn history (queries + answers) and the session's
context files. Multi-turn memory only works if you pass the session back on
every call.

## Lifecycle

| You send | What happens |
|---|---|
| no `session` field | a session is still auto-created; its name is returned in `sessionInfo.session` |
| `".../sessions/-"` | same — explicit "create new" |
| `".../sessions/{id}"` | continues that session (history available to the model) |
| `"isSessionLess": true` | exchange is not persisted (response still shows a synthetic `sessions/session-less-…` name) |

On `v1`, `sessionInfo` is returned on the final response object.

```bash
SESSION=$(echo "$RESPONSE" | jq -er '[.[] | .sessionInfo.session // empty] | last')
```

See [`04-multi-turn-session.sh`](../snippets/curl/04-multi-turn-session.sh)
for the full two-turn round trip
(captured output: [`outputs/04-multi-turn-session.json`](../outputs/04-multi-turn-session.json)).

## CRUD

```bash
# create explicitly (useful to upload files before the first query)
POST {ENGINE}/sessions              {"displayName": "my session"}

# list (newest first, filterable)
GET  {ENGINE}/sessions?pageSize=10&orderBy=update_time%20desc
GET  {ENGINE}/sessions?filter=display_name="quarterly review"

# get, optionally with every turn's full answer
GET  {ENGINE}/sessions/{id}?includeAnswerDetails=true

# pin to the top of the UI list
PATCH {ENGINE}/sessions/{id}?updateMask=isPinned    {"isPinned": true}

# delete
DELETE {ENGINE}/sessions/{id}
```

Supported list filters: `user_pseudo_id`, `state`, `display_name`, `starred`,
`is_pinned`, `labels`, `create_time`, `update_time`. Order by `update_time`,
`create_time`, `session_name`, `is_pinned`, `display_name` (append ` desc`).

All of these are wrapped in
[`05-session-crud.sh`](../snippets/curl/05-session-crud.sh).

## Behaviors worth knowing

- **Resource names can come back with the project number**, even if the
  request used the project ID. Parse resource names instead of string-matching
  the path you sent.
- **Auto-titling**: sessions created through streamAssist get a
  `displayName` generated from the first query (e.g. "Bar chart concept
  image"). Don't key any logic off display names.
- **Personalization can outlive one session.** Do not treat session deletion
  as a general user-data erasure mechanism.
- **File listing**: use the `v1alpha`
  `{session}:listSessionFileMetadata` method; see [08-files.md](08-files.md).
- Sessions are visible in the Gemini Enterprise UI for the same user —
  API-created sessions with odd display names will appear in the end user's
  history panel.
