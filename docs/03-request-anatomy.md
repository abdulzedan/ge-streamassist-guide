# 3. Request anatomy

```text
POST https://{host}/{version}/projects/{project}/locations/{location}/collections/default_collection/engines/{app}/assistants/{assistant}:streamAssist
```

Use `default_assistant` unless the app has another assistant. Host selection is
covered in [chapter 2](02-authentication.md).

## request body

```jsonc
{
  "query": { "text": "..." },
  "session": "projects/.../engines/.../sessions/123",
  "agentsSpec": {
    "agentSpecs": [{ "agentId": "deep_research" }]
  },
  "toolsSpec": {
    "webGroundingSpec": {},
    "vertexAiSearchSpec": {
      "dataStoreSpecs": [{
        "dataStore": "projects/{project-number}/locations/global/collections/default_collection/dataStores/{id}"
      }]
    },
    "imageGenerationSpec": {},
    "videoGenerationSpec": {}
  },
  "generationSpec": { "modelId": "gemini-2.5-flash" },
  "userMetadata": {
    "preferredLanguageCode": "fr-CA",
    "timeZone": "America/Toronto"
  }
}
```

Alpha-only fields used by this guide:

```jsonc
{
  "fileIds": ["4299134345303410947"],
  "assistSkippingMode": "REQUEST_ASSIST",
  "isSessionLess": true,
  "actionSpec": { "actionDisabled": true }
}
```

`query.parts[]` can carry text, document, Drive and person references. Use the
full REST schema when working with those input types.

## versions

Checked against Discovery revision `20260908` and the current REST pages:

| Field or method | v1 | v1beta | v1alpha |
|---|---:|---:|---:|
| `streamAssist` | yes | yes | yes |
| non-streaming `assist` | yes | yes | yes |
| `agentsSpec` | yes | yes | yes |
| `toolsSpec`, `generationSpec`, `userMetadata` | yes | yes | yes |
| session CRUD and `addContextFile` | yes | yes | yes |
| `downloadFile` | yes | yes | yes |
| `fileIds`, `assistSkippingMode`, `isSessionLess` | no | no | yes |
| `listSessionFileMetadata` | no | no | yes |
| agent list/get/register/update/delete | no | no | yes |

The REST pages document some alpha request fields that the JSON Discovery
document still omits. The snippets use raw REST for those fields.
