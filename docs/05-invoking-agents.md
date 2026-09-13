# 5. Invoking agents

List agents with `GET {assistant}/agents` on `v1alpha`. The definition tells
you how the agent was built; the invocation path is a separate question.

| Agent | Through Stream Assist |
|---|---|
| Core Assistant | yes |
| Deep Research | yes |
| Agent Designer chat agent | yes |
| workflow agent | no |
| registered ADK agent | no; use registry A2A |
| registered A2A agent | no; use registry A2A |

## Stream Assist agent call

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

`mentionMode` defaults to `DIRECT`: one mentioned agent is the top-level agent
for the turn. `TOOL` and `TOOL_WORKFLOW_DIRECT` have workflow-specific rules;
check the current schema before using them.

Do not use a planner `functionCall` as the only routing test. `diagnosticInfo`
is not guaranteed in current `v1` responses. Validate a domain-specific answer
and inspect returned agent metadata when present.

Unavailable, private or unsuitable agents do not have one reliable failure
shape. Check the agent state before invocation and handle HTTP errors,
mid-stream errors, `FAILED`, `SKIPPED` and empty successful answers.

Registered ADK/A2A agents are covered in [chapter 11](11-a2a.md).
