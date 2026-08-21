# 5. Invoking agents

## Agent types you'll see on an app

`GET {ASSISTANT}/agents` (snippet 06) returns every registered agent. The
definition key tells you what kind it is:

| Definition key | Meaning | Built with |
|---|---|---|
| `adkAgentDefinition` | high-code agent on Vertex AI Agent Engine / Agent Runtime (`provisionedReasoningEngine`) | ADK (Python) |
| `a2aAgentDefinition` | high-code agent behind an external A2A endpoint | any A2A server |
| `managedAgentDefinition` | Made-by-Google / managed agents (`deep_research`, Data Insights, …) | Google |
| `workflowAgentDefinition` | no-code workflow agents | Agent Designer |
| `lowCodeAgentDefinition` | low-code agents | Agent Designer |
| `skillAgentDefinition` | skill agents (e.g. file/Excel skills) | Agent Designer |
| `dialogflowAgentDefinition` | Dialogflow CX agent | Dialogflow |

States: `ENABLED`, `DISABLED`, `PRIVATE` (visible only to its creator),
`SUSPENDED`.

## Invoking one: `agentsSpec`

```json
{
  "query":   { "text": "Assess this loan file for compliance issues." },
  "session": ".../sessions/-",
  "agentsSpec": { "agentSpecs": [ { "agentId": "1030712722314703187" } ] }
}
```

The exact same shape works for **every** agent type — ADK, A2A, managed,
no-code. Only the ID changes ([snippet 08](../snippets/curl/08-invoke-specific-agent.sh)).

### What `agentsSpec` actually does (important)

`agentsSpec` scopes the orchestrator's *candidate set* to your agent — it does
**not** hard-force every query to it:

- Domain-relevant queries are routed to the agent (you can verify in the final
  chunk's `answer.diagnosticInfo.plannerSteps`, which shows a `planStep` with a
  `functionCall` bearing the agent's name).
- Meta/trivial queries ("what do you do?", "hello") may still be answered by
  the orchestrator itself, sounding like the base assistant.
- Greetings can be skipped entirely (`SKIPPED` /
  `NON_ASSIST_SEEKING_QUERY_IGNORED`) — that's the query classifier, not the
  agent. Add `"assistSkippingMode": "REQUEST_ASSIST"` to override.

If you need a **guaranteed** direct line to one agent with zero orchestrator
involvement, use the native A2A surface instead ([11-a2a.md](11-a2a.md)).

### Confirming the routing

```bash
# final chunk → diagnosticInfo.plannerSteps[]: queryStep → planStep(functionCall) → toolStep
jq '.[-1].answer.diagnosticInfo.plannerSteps' response.json
```

If there is no `functionCall` step, your agent was not invoked — the answer
came from the base assistant.

## Behavior with unavailable agents

Verified live:

| Target | Result |
|---|---|
| `PRIVATE` agent (not yours) | **no error** — behaves like the agent isn't there; with `REQUEST_ASSIST`: `state: FAILED` + mid-stream `FAILED_PRECONDITION` error chunk |
| `DISABLED` agent | same as above |
| Nonexistent agent ID | same as above |

There is **no 404 for a bad agent ID** on streamAssist. If your agent
"never answers", check `06-list-agents.sh` output for its state before
debugging anything else.

## Per-type notes

- **ADK (high-code)**: responses stream normally; the agent can attach
  `inlineData`/files. First-call latency includes Agent Engine cold start —
  expect several extra seconds after idle periods.
- **A2A**: same call shape; the A2A server's response is relayed through the
  stream. If the A2A backend is down you get `FAILED` mid-stream, not an HTTP
  error.
- **Managed / no-code (e.g. Data Insights)**: some agents return
  `state: SUCCEEDED` with **zero reply text** when they have nothing to say for
  the query type (verified: capability questions to a Data Insights agent).
  Always handle the empty-answer case; don't treat SUCCEEDED as "there is
  text".
- **`deep_research`**: special two-step flow — see
  [07-deep-research.md](07-deep-research.md).
- **Workflow / skill agents in `PRIVATE` state** are only invocable by their
  creator's identity.

## Multiple agents

`agentSpecs` is an array — you can offer several agents and let the planner
pick per query:

```json
"agentsSpec": { "agentSpecs": [ {"agentId": "A"}, {"agentId": "B"} ] }
```
