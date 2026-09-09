# Gemini Enterprise — Stream Assist API Guide

Ready guide to the Gemini Enterprise **Stream Assist
API** (`assistants:streamAssist`): the headless entry point for invoking a
Gemini Enterprise app, this includes: its base assistant, no-code agents, high-code
(ADK / A2A) agents, Deep Research, tools (web & data-store grounding, image
and video generation), sessions and file uploads — without the UI.

**Every snippet can be executed against a live Gemini Enterprise app.
** Captured (sanitized) responses live in
[`outputs/`](outputs/), and the full smoke suite
(`./scripts/run-all.sh`) passes 12/12 against a real app.

## Quick start

```bash
git clone <this-repo> && cd ge-streamassist-guide

# 1. find your app + agents (verifies auth at the same time)
./scripts/discover.sh <your-gcp-project-id>

# 2. configure (writes .env for you)
./scripts/setup-env.sh <your-gcp-project-id>   # or: make env + edit .env

# 3. first call
./snippets/curl/01-basic-stream-assist.sh "What can you do?"

# 4. optional: run everything
make smoke
```

Requirements: `gcloud` (authenticated), `curl`, `jq`, `python3`. IAM:
`discoveryengine.assistants.assist` on the app's project.

## The guide

| Chapter | Covers |
|---|---|
| [00 Glossary](docs/00-glossary.md) | the terms used throughout |
| [01 Overview](docs/01-overview.md) | surfaces, architecture, verified capability matrix |
| [02 Authentication](docs/02-authentication.md) | IAM, tokens, headers, hosts, corp-TLS note |
| [03 Request anatomy](docs/03-request-anatomy.md) | every request field + version matrix |
| [04 Sessions](docs/04-sessions.md) | lifecycle, CRUD, memory behaviors |
| [05 Invoking agents](docs/05-invoking-agents.md) | agent types, `agentsSpec` semantics, routing proof |
| [06 Tools](docs/06-tools.md) | web/data-store grounding, image & video generation |
| [07 Deep Research](docs/07-deep-research.md) | the two-step flow, contentKind markers |
| [08 Files](docs/08-files.md) | upload, `fileIds` queries, download quirks |
| [09 Parsing the stream](docs/09-parsing-the-stream.md) | wire format, assembly algorithm, edge cases |
| [10 Agent management](docs/10-agent-management.md) | register/update/delete, OAuth authorizations |
| [11 A2A](docs/11-a2a.md) | A2A registration + native direct-invocation surface |
| [12 Caveats & gotchas](docs/12-caveats-gotchas.md) | **32 verified gotchas — read before production** |
| [13 API reference](docs/13-api-reference.md) | condensed field-level reference |
| [14 Recipes](docs/14-recipes.md) | end-to-end FSI flows + production checklist |

## Snippets

| Directory | Contents |
|---|---|
| [`snippets/curl/`](snippets/curl/) | 26 runnable bash snippets, one capability each (01 basic → 26 routing diagnosis) |
| [`snippets/python/`](snippets/python/) | `GEClient` (true incremental stream decoding) + 6 examples |
| [`snippets/node/`](snippets/node/) | zero-dependency Node 18+ streaming client + example |
| [`snippets/http/`](snippets/http/) | VS Code / JetBrains REST-client collections |

All curl snippets read the same [`.env`](.env.example) via
[`common.sh`](snippets/curl/common.sh) — nothing to edit inside the scripts.

## Repository layout

```
docs/          the guide, chapter by chapter
snippets/      curl / python / node / http clients & examples
scripts/       discover.sh (find apps+agents), run-all.sh (smoke suite)
outputs/       real captured API responses (sanitized)
```

## Reproducing this repo's verification

```bash
make env && $EDITOR .env     # point at your own app
make smoke                   # 12 fast checks
make smoke-full              # + deep-research plan, image & video generation
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
