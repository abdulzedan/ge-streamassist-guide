# 5. Invoking agents

List agents with `GET {assistant}/agents` on `v1alpha`. The definition tells
you how the agent was built; the invocation path is a separate question.

| Agent | Through StreamAssist |
|---|---|
| Core Assistant | yes |
| Deep Research | yes |
| Agent Designer chat agent | yes |
| workflow agent | no |
| registered ADK agent | no; use registry A2A |
| registered A2A agent | no; use registry A2A |

## StreamAssist agent call

Use stable `v1`:

```json
{
  "query": {"text": "Review this package."},
  "session": "projects/.../engines/.../sessions/-",
  "agentsSpec": {
    "agentSpecs": [{"agentId": "AGENT_ID"}]
  }
}
```

Use the numeric ID at the end of the agent resource name. `deep_research` is
the documented special ID. A malformed ID can fall back without a clear error,
so validate it before sending the request.

`mentionMode` defaults to `DIRECT`. The REST schema contains `TOOL` and
`TOOL_WORKFLOW_DIRECT`, but Google's current StreamAssist guide says workflow
agents are not supported. Treat them as unsupported until the task guide and
schema agree and a controlled test proves the call route.

Do not use a planner `functionCall` as the only routing test. `diagnosticInfo`
is not guaranteed in current `v1` responses. Validate a domain-specific answer
and inspect returned agent metadata when present.

Unavailable, private or unsuitable agents do not have one reliable failure
shape. Check the agent state before invocation and handle HTTP errors,
mid-stream errors, `FAILED`, `SKIPPED` and empty successful answers.

Registered ADK/A2A agents are covered in [chapter 11](11-a2a.md).
