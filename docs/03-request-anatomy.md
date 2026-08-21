# 3. Request anatomy

## Endpoint

```
POST https://{host}/{version}/projects/{PROJECT}/locations/{LOCATION}/collections/default_collection/engines/{APP_ID}/assistants/{ASSISTANT_ID}:streamAssist
```

- `{host}`: see [02-authentication.md](02-authentication.md).
- `{version}`: `v1` (GA) or `v1alpha` (superset — what this repo uses).
- `{ASSISTANT_ID}`: `default_assistant` unless you created more.

## Full request body (v1alpha)

```jsonc
{
  // The user turn. Optional ONLY when fileIds are provided.
  "query": { "text": "..." },              // or "parts": [...] — see below

  // Session resource name, or ".../sessions/-" (or omit) to auto-create.
  "session": "projects/.../engines/.../sessions/123",

  // Pin the call to specific registered agent(s). v1alpha only.
  "agentsSpec": { "agentSpecs": [ { "agentId": "236556840724368325" } ] },

  // Context files previously uploaded to THIS session. v1alpha only.
  "fileIds": [ "4299134345303410947" ],

  // Tools for this request (all optional; empty object = enabled).
  "toolsSpec": {
    "webGroundingSpec": {},
    "vertexAiSearchSpec": {
      "dataStoreSpecs": [ {
        "dataStore": "projects/{PROJECT_NUMBER}/locations/global/collections/default_collection/dataStores/{DS_ID}",
        "filter": "category: ANY(\"reports\")",
        "boostSpec": { "conditionBoostSpecs": [ ... ] }
      } ],
      "filter": "..."
    },
    "imageGenerationSpec": {},
    "videoGenerationSpec": {}
  },

  // Override the engine's default answer model for this call.
  "generationSpec": { "modelId": "gemini-2.5-flash" },

  // Disable the "is this worth answering?" classifier (see gotchas).
  "assistSkippingMode": "REQUEST_ASSIST",       // v1alpha only

  // Fallback language + time zone.
  "userMetadata": { "preferredLanguageCode": "fr-CA", "timeZone": "America/Toronto" },

  // Don't persist this exchange as a session turn. v1alpha only.
  "isSessionLess": true,

  // Enterprise edition: turn actions (connector write-backs) off.
  "actionSpec": { "actionDisabled": true }
}
```

## `query.parts` — richer inputs than plain text

`query` accepts `parts[]` instead of (or alongside) `text`:

| Part | Purpose |
|---|---|
| `text` | plain text fragment |
| `documentReference { documentName }` | point at a document already indexed in a data store |
| `driveDocumentReference { driveId }` | point at a Google Drive file |
| `personReference { email / personId }` | people-aware queries |
| `mimeType` | MIME of the part (default `text/plain`) |

## Version availability (verified against the public discovery documents)

| Field / method | v1 | v1beta | v1alpha |
|---|---|---|---|
| `streamAssist` (query, session, toolsSpec, generationSpec, userMetadata) | ✅ | ✅ | ✅ |
| `agentsSpec` | — | — | ✅ * |
| `fileIds` | — | — | ✅ * |
| `assistSkippingMode`, `isSessionLess` | — | — | ✅ * |
| `sessions.addContextFile` | ✅ | ✅ | ✅ |
| `assistants.agents` CRUD (list/get/register/patch/delete) | — | — | ✅ |
| `sessions` CRUD | ✅ | ✅ | ✅ |
| non-streaming `:assist` | undocumented everywhere; works on v1alpha today |

\* These fields are accepted and functional on the live v1alpha endpoint but
are **not present in the public discovery document** — they come from the
Gemini Enterprise product docs (and are proven by the captured outputs in this
repo). Generated client libraries built from the discovery doc won't expose
them; call REST directly (or use this repo's Python client) when you need them.

## Minimal requests per use case

```bash
# Plain question
{"query": {"text": "..."}}

# Continue a conversation
{"query": {"text": "..."}, "session": "<sessionInfo.session from last call>"}

# Force a specific agent
{"query": {"text": "..."}, "session": ".../sessions/-",
 "agentsSpec": {"agentSpecs": [{"agentId": "<id>"}]}}

# Ask about an uploaded file
{"query": {"text": "..."}, "session": "<upload session>", "fileIds": ["<fileId>"]}
```
