# 13. Condensed API reference

Current as of Discovery revision `20260908`. `G`, `B` and `A` mean `v1`,
`v1beta` and `v1alpha`.

## methods

| Method | Path | Versions |
|---|---|---|
| Stream Assist | `POST {assistant}:streamAssist` | G B A |
| Assist | `POST {assistant}:assist` | G B A |
| session create/get/list/update/delete | `{engine}/sessions[...]` | G B A |
| add context file | `POST {session}:addContextFile` | G B A |
| download file | `GET {session}:downloadFile` | G B A |
| list session file metadata | `GET {session}:listSessionFileMetadata` | A |
| agent list/get/create/update/delete/deploy/review | `{assistant}/agents[...]` | A |
| registry A2A card/message | `{a2a-endpoint}/v1/...` | G |

## StreamAssistRequest

| Field | Versions | Note |
|---|---|---|
| `query.text`, `query.parts[]` | G B A | user input |
| `session` | G B A | full resource name; `-` creates |
| `agentsSpec.agentSpecs[]` | G B A | supported agent types only |
| `toolsSpec` | G B A | web, Vertex AI Search, image, video |
| `generationSpec.modelId` | G B A | request model override |
| `userMetadata` | G B A | language fallback and time zone |
| `fileIds[]` | A | files from the same session |
| `assistSkippingMode` | A | `REQUEST_ASSIST` |
| `isSessionLess` | A | do not persist turn |
| `actionSpec.actionDisabled` | A | action control |

## StreamAssistResponse

| Field | Note |
|---|---|
| `answer.state` | `IN_PROGRESS`, `SUCCEEDED`, `FAILED`, `SKIPPED`, `CANCELLED` |
| `answer.replies[].groundedContent.content` | text, thought, file and other content parts |
| `contentMetadata` | `contentKind`, `contentId` |
| grounding and citation metadata | references and grounded segments |
| `assistSkippedReasons[]` | why the turn was skipped |
| `diagnosticInfo` | optional planner detail |
| `sessionInfo` | session and query identifiers; final object on `v1` |
| `assistToken` | support correlation token |

## session file metadata

`fileMetadata[]` may include `fileId`, `name`, `mimeType`, `byteSize`,
`tokenCount`, `quotaPercentage`, `selected`, `usedInConversation`,
`originalUri`, `originalSourceType`, `uploadTime`, `metadata` and `session`.

Download the current schemas when exact fields matter:

```bash
curl -sS "https://discoveryengine.googleapis.com/\$discovery/rest?version=v1" > de-v1.json
curl -sS "https://discoveryengine.googleapis.com/\$discovery/rest?version=v1alpha" > de-v1alpha.json
```
