# 1. Overview

Stream Assist is the conversational API for a Gemini Enterprise app. It
handles the base assistant, sessions, connected data, tools, Agent Designer
chat agents and Deep Research.

Registered ADK and A2A agents use the registry A2A endpoint. They are not
supported through `streamAssist`.

```text
application
  ├─ Stream Assist
  │    ├─ core assistant
  │    ├─ Agent Designer chat agent
  │    ├─ Deep Research
  │    └─ grounding, files and media tools
  └─ registry A2A endpoint
       └─ agent advertising an A2A protocol
```

## invocation surfaces

| Surface | Endpoint | Use it for |
|---|---|---|
| Stream Assist | `POST {assistant}:streamAssist` | conversations, supported agents, tools, files and grounding |
| Assist | `POST {assistant}:assist` | the same request as one non-streaming response |
| Registry A2A | `POST {a2a-url}/v1/message:stream` | direct calls to an agent that advertises A2A |

Agent list/get is a separate `v1alpha` control-plane surface. Discovering an
agent does not mean that every invocation surface supports it.

## checked capabilities

| Capability | Current path | Live check |
|---|---|---|
| base query and multi-turn session | Stream Assist `v1` | yes |
| unary assist | Assist `v1` | yes |
| Agent Designer chat agent | `agentsSpec` on Stream Assist `v1` | yes |
| Deep Research | `agentsSpec` on Stream Assist `v1` | yes |
| registered ADK/A2A agent | registry A2A endpoint | yes; may return an auth or confirmation handoff |
| web and data-store grounding | `toolsSpec` on Stream Assist `v1` | yes |
| image and video generation | `toolsSpec` on Stream Assist `v1` | yes |
| file upload and download | session methods on `v1` | yes |
| file selection and metadata list | `v1alpha` | yes |

The detailed run record is in [chapter 16](16-verification.md). Captured
payload shapes are in [`outputs/`](../outputs/).
