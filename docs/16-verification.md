# 16. Verification record

Last checked: 2026-09-13.

## sources

- [Stream Assist v1 REST reference](https://docs.cloud.google.com/gemini/enterprise/docs/reference/rest/v1/projects.locations.collections.engines.assistants/streamAssist)
- [Call a specific agent](https://docs.cloud.google.com/gemini/enterprise/docs/invoke-agent-streamassist)
- [Call an agent through its registry A2A endpoint](https://docs.cloud.google.com/gemini/enterprise/docs/invoke-agent-a2a)
- [Deep Research](https://docs.cloud.google.com/gemini/enterprise/docs/research-assistant)
- [A2A registration](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent)
- [ADK registration](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-adk-agent)
- [Session file metadata](https://docs.cloud.google.com/gemini/enterprise/docs/reference/rest/v1alpha/projects.locations.collections.engines.sessions/listSessionFileMetadata)
- [Quotas and overages](https://docs.cloud.google.com/gemini/enterprise/docs/quotas-and-overages)

The `v1`, `v1beta` and `v1alpha` JSON Discovery documents were downloaded
again. All reported revision `20260908`.

## live target

Checks used the normal active gcloud configuration and user ADC for the
Altostrat `main-env-demo` project. No alternate gcloud configuration or
GenXpress credential path was used.

| Area | Result |
|---|---|
| versions | `streamAssist` and `assist` returned HTTP 200 and `SUCCEEDED` on `v1`, `v1beta` and `v1alpha` |
| supported agents | Deep Research and an Agent Designer chat agent answered through `agentsSpec` |
| unsupported Stream Assist agents | registered ADK/A2A IDs produced base-assistant behavior with no routing evidence, matching the current documented limitation |
| native A2A | cards and message streams worked for A2A-capable agents; some returned authorization or confirmation handoffs instead of text |
| Agent Registry | API enabled; live records advertised `A2A_AGENT` in global, us and eu locations |
| non-A2A agent | Deep Research card returned 501 and message returned 400 |
| sessions | create, continue, list, get, pin and delete were exercised by the smoke path or direct checks |
| file lifecycle | upload on `v1`; metadata list on `v1alpha`; file query on `v1alpha`; downloads on all three versions; downloaded bytes matched |
| grounding | live web and selected data-store calls returned grounded content; the data-store path used the project number |
| media | image and video calls returned downloadable PNG and MP4 files |
| research | plan and execution completed with research markers, references, report text and an MP3 summary |
| IAM | the current `roles/discoveryengine.user` definition includes assist and session file permissions; management operations still require their specific permissions |
| soak infrastructure | three Cloud Run Jobs existed and were ready; three schedulers were paused; final report artifacts existed in GCS |

Temporary media and response files were removed after the run. Exact audit
sessions were deleted where they were tracked directly. The smoke suite now
tracks session IDs and deletes them on exit.

## limits of the proof

- This is one project, identity, region and date; it is not an SLA.
- A successful response does not prove that a particular licence counter moved.
- Grounded content depends on caller ACLs and the app's connected sources.
- Alpha fields and Discovery/documentation mismatches need rechecking before a release.
- OAuth-required A2A flows need an end-user completion step; the audit stopped at the handoff.
