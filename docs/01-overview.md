# 1. Overview

## What Stream Assist is

`assistants:streamAssist` is the headless (API) entry point to a Gemini
Enterprise app. One HTTP POST gives you programmatic access to everything the
Gemini Enterprise UI can do:

- the base assistant (grounded on your connected data stores and/or web search),
- every **agent** registered on the app — no-code (Agent Designer / managed),
  high-code (ADK on Agent Engine / Agent Runtime), A2A, Dialogflow,
- **Deep Research**,
- tools: web grounding, data-store grounding, image generation, video generation,
- sessions (multi-turn memory) and context files (upload → ask → download).

```
your code ──POST :streamAssist──▶ default_assistant (orchestrator/planner)
                                        │
              ┌─────────────┬───────────┼──────────────┬───────────────┐
              ▼             ▼           ▼              ▼               ▼
        base answer   ADK agents   A2A agents   no-code agents   deep_research
        (RAG + web)   (Agent       (external    (Agent Designer, (made by
                       Engine)      endpoint)    managed)         Google)
```

## The two invocation surfaces

| Surface | Endpoint | What it does |
|---|---|---|
| **streamAssist** | `POST .../assistants/default_assistant:streamAssist` | Goes through the orchestrator. Sessions, files, tools, agent routing. This is what the Gemini Enterprise UI itself uses. |
| **Native A2A** | `POST .../assistants/default_assistant/agents/{id}/a2a/v1/message:stream` | Talks to ONE registered agent directly, A2A protocol, no orchestrator in between. See [11-a2a.md](11-a2a.md). |

Rule of thumb: use streamAssist when you want the full assistant experience
(grounding, sessions, routing); use the native A2A surface when you need a
guaranteed direct line to one specific agent.

## Verified capability matrix

Everything below was executed against a live Gemini Enterprise app before
being documented (captured responses in [`outputs/`](../outputs/)):

| Capability | Snippet | Works | Notes |
|---|---|---|---|
| Basic query | curl 01/02 | ✅ | |
| Sessions & multi-turn | curl 03-05 | ✅ | auto-create with `-` |
| List/get agents | curl 06-07 | ✅ | v1alpha only |
| Invoke ADK (high-code) agent | curl 08 | ✅ | `agentsSpec` |
| Invoke A2A agent | curl 08 | ✅ | same `agentsSpec` shape |
| Invoke no-code / managed agent | curl 08 | ✅ | some return empty text — see gotchas |
| Deep Research (plan + execute) | curl 09-10 | ✅ | allowlisted API feature |
| Web grounding | curl 11 | ✅ | assistant-level setting required |
| Data store grounding | curl 12 | ✅ | filter + boost supported |
| Image generation | curl 13 | ✅ | returns session fileId |
| Video generation | curl 14 | ✅ | returns session fileId |
| File upload + file Q&A | curl 15-16 | ✅ | `addContextFile` + `fileIds` |
| Download session files | curl 17 | ✅ | `alt=media` + follow redirect |
| Non-streaming `:assist` | curl 18 | ✅ | undocumented; best-effort |
| Skip-mode override | curl 19 | ✅ | `REQUEST_ASSIST` |
| Language & user metadata | curl 20 | ✅ | fallback only, not a force |
| Per-request model override | curl 21 | ✅ | `generationSpec.modelId` |
| Native A2A card + message:stream | curl 23-24 | ✅ | direct agent line |

## Editions and availability

- streamAssist request/response is GA in `v1`; **agent management, `agentsSpec`,
  `fileIds` and several other fields require `v1alpha`** (this repo defaults to
  v1alpha). See [03-request-anatomy.md](03-request-anatomy.md).
- Deep Research via API is GA **with allowlist** — request it via your Google
  account team if calls to `deep_research` fail.
- Made-by-Google agents (Deep Research, Core Assistant extras) are not
  available in the Frontline edition.
- `actionSpec.actionDisabled` only works on Enterprise edition.

## Reading order

New to the API? Read chapters 2 → 3 → 9 first (auth, request shape, stream
parsing), then jump to the capability you need. Chapter 12 (caveats & gotchas)
is worth a full read before you write production code.
