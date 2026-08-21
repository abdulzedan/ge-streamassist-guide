# 10. Agent management (register / update / delete)

Everything here is **v1alpha** and needs admin-level permissions (Gemini
Enterprise Admin). The read-only calls are wrapped in snippets 06/07.

## List / get

```
GET {ASSISTANT}/agents?pageSize=100
GET {ASSISTANT}/agents/{AGENT_ID}
```

The agent ID is the trailing number of `name`. The definition key
(`adkAgentDefinition` / `a2aAgentDefinition` / …) identifies the type
(see chapter 5).

## Register a high-code ADK agent

Prereq: the agent is deployed to Vertex AI Agent Engine ("Agent Runtime") as a
`reasoningEngines/{id}` resource.

```bash
POST {ASSISTANT}/agents
{
  "displayName": "Financial Advisor",
  "description": "Handles stock research, quotes and portfolio questions.",
  "icon": { "uri": "https://…/icon.png" },
  "adkAgentDefinition": {
    "provisionedReasoningEngine": {
      "reasoningEngine": "projects/{PROJECT}/locations/{REGION}/reasoningEngines/{ID}"
    }
  }
}
```

Notes (from the official registration guide, verified where possible):

- **`description` is the router prompt.** The orchestrator reads it to decide
  when to route to your agent. Vague description ⇒ agent never invoked.
- **Location compatibility**: app `global` → Agent Engine in any region;
  app `us` → `us-*` regions only; app `eu` → `europe-*` only.
- Cross-project registration is supported (VPC-SC compliant).
- The agent receives the end user's email for personalization.
- Model Armor configured in the console does NOT protect ADK agents — enforce
  it inside the agent's code.

## OAuth for agent tools (authorization resources)

If agent tools act on behalf of the user, create an authorization resource
first, then reference it at registration:

```bash
POST https://{host}/v1alpha/projects/{PROJECT_NUMBER}/locations/{LOCATION}/authorizations?authorizationId={AUTH_ID}
{
  "name": "projects/{PROJECT_NUMBER}/locations/{LOCATION}/authorizations/{AUTH_ID}",
  "serverSideOauth2": {
    "clientId": "…", "clientSecret": "…",
    "authorizationUri": "https://accounts.google.com/o/oauth2/v2/auth?client_id=…&redirect_uri=https%3A%2F%2Fvertexaisearch.cloud.google.com%2Fstatic%2Foauth%2Foauth.html&scope=…&include_granted_scopes=true&response_type=code&access_type=offline&prompt=consent",
    "tokenUri": "https://oauth2.googleapis.com/token"
  }
}
```

then in the agent: `"authorizationConfig": { "toolAuthorizations":
["projects/{PROJECT_NUMBER}/locations/{LOCATION}/authorizations/{AUTH_ID}"] }`
(A2A agents use the singular `agentAuthorization` instead).

Register both redirect URIs on the OAuth client:
`https://vertexaisearch.cloud.google.com/oauth-redirect` and
`…/static/oauth/oauth.html`. Request at least one sensitive scope, or the
Authorize button never appears and tools silently lack tokens.

## Update / delete

```
PATCH  {ASSISTANT}/agents/{AGENT_ID}     # displayName, description, definition
DELETE {ASSISTANT}/agents/{AGENT_ID}     # returns a completed LRO
```

Teardown order for ADK agents: **unregister from the assistant first, then
undeploy the reasoning engine** — deleting the engine first leaves a broken
registration that still shows up in the UI.

## Import files to an agent

`POST {ASSISTANT}/agents/{AGENT_ID}/files:import` exists in v1alpha
(`ImportAgentFileRequest`) for attaching reference files to an agent
definition — niche, but useful for skill-style agents.
