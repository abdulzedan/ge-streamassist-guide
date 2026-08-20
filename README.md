# Gemini Enterprise — Stream Assist API Guide

A hands-on, copy-paste-ready guide to the Gemini Enterprise **Stream Assist API**
(`assistants:streamAssist`): the headless entry point for invoking a Gemini
Enterprise app — its base assistant, no-code agents, high-code (ADK / A2A)
agents, Deep Research, tools, sessions, and file uploads — without the UI.

Every snippet in this repository was executed against a live Gemini Enterprise
app before being committed. Captured (sanitized) responses live in
[`outputs/`](outputs/) so you can see exactly what to expect before you run
anything.

## Quick start

```bash
git clone <this-repo>
cd ge-streamassist-guide
cp .env.example .env   # fill in PROJECT_ID / LOCATION / APP_ID
./scripts/discover.sh  # verifies auth and lists your apps + agents
./snippets/curl/01-basic-stream-assist.sh "What can you do?"
```

## Repository layout

| Path | What's in it |
|---|---|
| `docs/` | The guide, chapter by chapter |
| `snippets/curl/` | Runnable bash/curl snippets — one capability each |
| `snippets/python/` | A minimal Python client + examples |
| `scripts/` | Discovery, bootstrap and run-everything helpers |
| `outputs/` | Real captured API responses (sanitized) |

## The guide

Start with [docs/01-overview.md](docs/01-overview.md).
