# 2. Authentication & prerequisites

## Prerequisites

1. A Gemini Enterprise app (engine). Find its ID with `./scripts/discover.sh <project-id>`.
2. The **Discovery Engine API** enabled in the project
   (`gcloud services enable discoveryengine.googleapis.com`).
3. An identity holding the IAM permission **`discoveryengine.assistants.assist`**
   (e.g. `roles/discoveryengine.user` or broader). File upload additionally
   needs `discoveryengine.sessions.addContextFile`; agent management needs
   admin-level Discovery Engine roles.

## Getting a token

Every request is a normal OAuth2 bearer-token call:

```bash
TOKEN=$(gcloud auth print-access-token)

curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1alpha/.../assistants/default_assistant:streamAssist" \
  -d '{ "query": { "text": "Hello" } }'
```

Required scope: `https://www.googleapis.com/auth/cloud-platform`
(`discoveryengine.readwrite` also works for most calls).

### User credentials vs service account

| | User (`gcloud auth login`) | Service account |
|---|---|---|
| Good for | exploration, this repo's snippets | production backends |
| Data-store ACLs | enforced as that user (Drive/SharePoint/Gmail results are the user's own) | SA sees only what the SA can see |
| Personalization / memory | tied to the user | tied to the SA identity |

Because Gemini Enterprise apps sit on top of ACL-aware connectors, **who calls
matters**: the same query can return different grounding results per identity.
For end-user-facing backends, either call as the end user (OAuth) or accept
that a service account has its own (usually narrower) view of the data.

## The `X-Goog-User-Project` header

Always send `X-Goog-User-Project: <project-id>`. Without it, quota/billing
attribution falls back to the OAuth client's default project, which for user
credentials commonly produces
`403 PERMISSION_DENIED (CONSUMER_INVALID / USER_PROJECT_DENIED)` errors that
look like IAM problems but aren't.

## Endpoint host per location

| App location | Host |
|---|---|
| `global` | `discoveryengine.googleapis.com` |
| `us` | `us-discoveryengine.googleapis.com` |
| `eu` | `eu-discoveryengine.googleapis.com` |

Using the wrong host for your app's location returns 404s (or, worse, an empty
resource list that sends you debugging in the wrong direction). `common.sh`
derives the host from `LOCATION` automatically.

## Common auth failures

| Error | Actual cause |
|---|---|
| `USER_PROJECT_DENIED` / `Project not found or deleted` | The project in the URL/header is not the project that hosts the app — remember apps display an app *name* in the UI; the GCP project ID may differ. |
| `PERMISSION_DENIED on resource project` | `X-Goog-User-Project` missing or points at a project where the caller lacks `serviceusage.services.use`. |
| `403 ... discoveryengine.assistants.assist` | Missing Discovery Engine role on the caller. |
| `401 UNAUTHENTICATED` | Token expired (user tokens last ~1h — mint per call like `common.sh` does). |
