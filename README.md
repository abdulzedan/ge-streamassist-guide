# Gemini Enterprise Stream Assist API guide

Runnable REST, Python and Node examples for calling a Gemini Enterprise app
without the web UI. The guide covers Stream Assist, sessions, files, grounding,
media generation, Deep Research, agent discovery and native A2A calls.

The examples default to stable `v1`. Snippets that need agent discovery,
`fileIds`, `isSessionLess`, `assistSkippingMode` or file metadata select
`v1alpha` themselves.

## quick start

```bash
git clone <this-repo>
cd ge-streamassist-guide

./scripts/discover.sh <gcp-project-id>
./scripts/setup-env.sh <gcp-project-id>
./snippets/curl/01-basic-stream-assist.sh "What can you do?"
make smoke
```

Requirements: `gcloud`, `curl`, `jq` and Python 3. IAM must include
`discoveryengine.assistants.assist`; individual file and control-plane methods
have their own permissions.

## guide

| Chapter | Subject |
|---|---|
| [00](docs/00-glossary.md) | glossary |
| [01](docs/01-overview.md) | surfaces and supported paths |
| [02](docs/02-authentication.md) | auth, IAM, headers and regional hosts |
| [03](docs/03-request-anatomy.md) | request fields and API versions |
| [04](docs/04-sessions.md) | sessions and multi-turn state |
| [05](docs/05-invoking-agents.md) | supported Stream Assist agents |
| [06](docs/06-tools.md) | web, data-store and media tools |
| [07](docs/07-deep-research.md) | plan and execution flow |
| [08](docs/08-files.md) | upload, query, list and download |
| [09](docs/09-parsing-the-stream.md) | streamed JSON-array parsing |
| [10](docs/10-agent-management.md) | agent registration and auth resources |
| [11](docs/11-a2a.md) | direct A2A invocation |
| [12](docs/12-caveats-gotchas.md) | short production notes |
| [13](docs/13-api-reference.md) | condensed REST reference |
| [14](docs/14-recipes.md) | composed examples |
| [15](docs/15-soak-test.md) | soak-test method and results |
| [16](docs/16-verification.md) | source and live verification record |

## repository

| Path | Contents |
|---|---|
| [`snippets/curl/`](snippets/curl/) | 27 runnable shell examples |
| [`snippets/python/`](snippets/python/) | incremental client and 8 examples |
| [`snippets/node/`](snippets/node/) | zero-dependency streaming client |
| [`snippets/http/`](snippets/http/) | REST-client requests |
| [`soak/`](soak/README.md) | Cloud Run reliability harness |
| [`outputs/`](outputs/README.md) | sanitized response shapes |

```bash
make validate       # offline tests used by CI
make smoke          # live, fast checks against .env
make smoke-full     # adds a research plan and media generation
```

Apache 2.0. See [LICENSE](LICENSE).
