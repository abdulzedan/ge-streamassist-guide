# 13. Condensed API reference

Field-level reference distilled from the public discovery documents
(rev. 2026-08) plus live-verified fields that the discovery docs omit
(marked ⚠ undocumented). Versions: G = v1 (GA), B = v1beta, A = v1alpha.

## Methods

| Method | HTTP | Versions |
|---|---|---|
| streamAssist | `POST {assistant}:streamAssist` | G B A |
| assist (non-streaming) | `POST {assistant}:assist` | ⚠ works on A |
| sessions.create/get/list/patch/delete | `{engine}/sessions[...]` | G B A |
| sessions.addContextFile | `POST {session}:addContextFile` | G B A (Preview) |
| sessions.downloadFile | `GET {session}:downloadFile?fileId=&alt=media` | ⚠ works on A |
| sessions.listFiles | `GET {session}:listFiles` | A (ownership-restricted) |
| sessions.assistAnswers.get | `GET {session}/assistAnswers/{id}` | G B A |
| assistants.get/patch/list/create/delete | `{engine}/assistants[...]` | G B A |
| agents.list/get/create/patch/delete | `{assistant}/agents[...]` | A |
| agents.files.import | `POST {agent}/files:import` | A |
| native A2A: card / message:send / message:stream / tasks.* | `{agent}/a2a/v1/...` | G |
| authorizations.create/... | `projects/{num}/locations/{loc}/authorizations` | A |

## StreamAssistRequest

| Field | Type | Ver | Notes |
|---|---|---|---|
| `query.text` | string | G B A | optional if `fileIds` set |
| `query.parts[]` | QueryPart | G B A | text / documentReference / driveDocumentReference / personReference / mimeType |
| `session` | string | G B A | resource name; `-`/empty = create |
| `userMetadata.preferredLanguageCode` | string | G B A | fallback only |
| `userMetadata.timeZone` | string | G B A | IANA tz |
| `generationSpec.modelId` | string | G B A | per-request model override |
| `toolsSpec.vertexAiSearchSpec` | object | G B A | `dataStoreSpecs[]{dataStore(number!), filter, numResults, boostSpec, customSearchOperators}`, `filter` |
| `toolsSpec.webGroundingSpec` | `{}` | G B A | needs assistant webGroundingType |
| `toolsSpec.imageGenerationSpec` | `{}` | G B A | file reply |
| `toolsSpec.videoGenerationSpec` | `{}` | G B A | file reply |
| `actionSpec.actionDisabled` | bool | A | Enterprise edition |
| `agentsSpec.agentSpecs[].agentId` | string | ⚠ A | pin agent(s) |
| `fileIds[]` | string | ⚠ A | session context files |
| `assistSkippingMode` | enum | ⚠ A | `REQUEST_ASSIST` |
| `isSessionLess` | bool | ⚠ A | don't persist turn |
| `answerGenerationMode` | enum | ⚠ A | NORMAL / RESEARCH / AGENT (prefer agentsSpec) |
| `agentsConfig.agent` | string | ⚠ A | full agent resource name (project number) |
| `cannedQuery` | string | ⚠ A | new sessions only |

## StreamAssistResponse

| Field | Notes |
|---|---|
| `answer` | AssistAnswer (below); may be absent on no-op chunks |
| `sessionInfo.session`, `.queryId` | continue the conversation with `session` |
| `assistToken` | correlation ID for support |
| `invocationTools[]`, `invokedSkills[]` | names of tools/skills used |
| `connectorAuthErrors[]` | per-connector auth failures (request still proceeds) |

## AssistAnswer

| Field | Notes |
|---|---|
| `state` | IN_PROGRESS → SUCCEEDED / FAILED / SKIPPED / CANCELLED |
| `replies[].groundedContent.content` | `text` + `thought`, `file{fileId,mimeType}`, `inlineData{mimeType,data}`, `executableCode{code}`, `codeExecutionResult{outcome,output}`, `role` |
| `replies[].groundedContent.contentMetadata` | `contentKind` (RESEARCH_* markers), `contentId` |
| `replies[].groundedContent.textGroundingMetadata` | `references[].documentMetadata{document,uri,title,pageIdentifier,domain}`, `segments[]{startIndex,endIndex,groundingScore,referenceIndices}` |
| `replies[].groundedContent.citationMetadata` | `citations[]{startIndex,endIndex,title,uri,license,publicationDate}` |
| `replies[].replyId` | groups fragments of one logical reply |
| `assistSkippedReasons[]` | NON_ASSIST_SEEKING_QUERY_IGNORED, CUSTOMER_POLICY_VIOLATION |
| `customerPolicyEnforcementResult` | verdict ALLOW/BLOCK, violationSource SYSTEM/PROMPT/ATTACHMENT, banned phrases, Model Armor detail |
| `diagnosticInfo.plannerSteps[]` | queryStep / planStep(functionCall) / toolStep(functionResult) — routing trace |
| `name` | `.../sessions/{s}/assistAnswers/{id}` — final chunk only |

## Session

| Field | Notes |
|---|---|
| `name` | `.../engines/{e}/sessions/{id}` |
| `displayName` | auto-titled from first query if unset |
| `state` | IN_PROGRESS |
| `isPinned`, `labels[]`, `userPseudoId` | list-filterable |
| `turns[]` | `query`, `detailedAssistAnswer` (with `includeAnswerDetails=true`) |
| `pendingAsyncAssistOperationId` | set while an async assist runs |

List filters: `user_pseudo_id, state, display_name, starred, is_pinned,
labels, create_time, update_time`; orderBy: `update_time, create_time,
session_name, is_pinned, display_name` (+` desc`).

## Agent (v1alpha)

| Field | Notes |
|---|---|
| `displayName`, `description` | description = router prompt |
| `state` | CONFIGURED / CREATING / CREATION_FAILED / DEPLOYING / DEPLOYMENT_FAILED / PRIVATE / ENABLED / DISABLED / SUSPENDED |
| `adkAgentDefinition.provisionedReasoningEngine.reasoningEngine` | Agent Engine resource |
| `a2aAgentDefinition.jsonAgentCard` | escaped agent-card JSON (A2A v0.3) |
| `managedAgentDefinition` | Made-by-Google (e.g. `deep_research`) |
| `dialogflowAgentDefinition` | Dialogflow CX |
| `workflowAgentDefinition` / `lowCodeAgentDefinition` / `skillAgentDefinition` | ⚠ observed live; not in public discovery docs |
| `authorizationConfig` | `toolAuthorizations[]` (ADK) / `agentAuthorization` (A2A) |
| `starterPrompts[]`, `icon`, `sharingConfig`, `observabilityConfig` | UI/metadata |

## FileMetadata (sessions files)

`fileId`, `name`, `mimeType`, `byteSize`, `downloadUri`, `uploadTime`,
`lastAddTime`, `fileOriginType` (USER_PROVIDED / AI_GENERATED /
INTERNALLY_GENERATED), `originalSourceType` (INLINE / LOCAL / CLOUD_STORAGE /
CLOUD_DRIVE / URL), `views{thumbnail,…}`.

Full extracted schemas (97 objects, every field and enum) available in the
upstream discovery documents; regenerate anytime:

```bash
curl -s "https://discoveryengine.googleapis.com/\$discovery/rest?version=v1alpha" > de-v1alpha.json
```
