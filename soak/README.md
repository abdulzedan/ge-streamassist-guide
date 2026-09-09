# 24-hour soak test for the Stream Assist API

A small harness that calls the Gemini Enterprise Stream Assist API **every
5 minutes for 24 hours from Cloud Run** (not from a laptop), exercises every
capability the guide documents, counts what it used against the licence
quota, and renders the evidence into a report artifact.

```
Cloud Scheduler ──every 5 min──▶ Cloud Run Job ge-soak-fast   ─┐
Cloud Scheduler ──every 4 h────▶ Cloud Run Job ge-soak-heavy  ─┼─▶ gs://<bucket>/runs/YYYY-MM-DD/*.json
Cloud Scheduler ──hourly───────▶ Cloud Run Job ge-soak-report ─┘        └─▶ gs://<bucket>/reports/latest/{report.md,report.json,*.csv}
```

All three jobs run the same image (`soak/Dockerfile`, built by Cloud Build
from the repo root so it reuses `snippets/python/ge_streamassist.py`). The
jobs run as the service account `ge-soak@<project>.iam.gserviceaccount.com`
with `roles/discoveryengine.user` + `viewer`, i.e. a plain headless caller
with no Gemini Enterprise licence assigned.

## Quick start

```bash
./soak/deploy.sh deploy        # APIs, SA, bucket, image, 3 jobs, 3 schedulers (created paused)
./soak/deploy.sh run fast      # one manual execution; check it wrote runs/... to the bucket
./soak/deploy.sh start 24      # campaign.json: start at the next 5-min mark, end 24h later; schedulers resumed
./soak/deploy.sh status        # any time
./soak/deploy.sh report final  # after the window: report rendered for the campaign window, downloaded to soak/out/final/
./soak/deploy.sh stop          # early stop (pauses schedulers, closes the window)
./soak/deploy.sh destroy       # remove schedulers + jobs (bucket and SA are kept)
```

`make soak-deploy / soak-start / soak-status / soak-report` wrap the same
commands. Everything reads the repo `.env` for the target app.

## What runs, and how often (profile `standard`)

| Check | Cadence | Assistant queries / day | What it proves |
|---|---|---|---|
| `control_plane` | every run | 0 | agents.list/get, assistants.get, engines.get, sessions.list answer |
| `probe` | every 5 min (288/day) | 288 | sessionless `streamAssist` returns SUCCEEDED + text (availability + latency series) |
| `multiturn` | every 30 min | 96 | session memory across two turns, `sessions.get` shows the turns, delete works |
| `agent_adk` | every 30 min | 48 | `agentsSpec` pinned to an ADK agent answers; observation: planner really routed (`plannerSteps` functionCall) |
| `agent_a2a` | every 30 min | 48 | same for a registered A2A agent |
| `a2a_native` | every 30 min | 48 | native `a2a/v1/card` + `message:stream` direct line |
| `web_grounding` | every 30 min | 48 | `webGroundingSpec`; observation: grounding references present |
| `datastore_grounding` | every 30 min | 48 | `vertexAiSearchSpec` on one data store; observation: references present |
| `file_roundtrip` | every hour | 24 | `addContextFile` -> `listSessionFileMetadata` -> `fileIds` query answers from the file -> `downloadFile` bytes match |
| `assist_nonstreaming` | every hour | 24 | undocumented `:assist` still works |
| `skip_mode` | every hour | 48 | "hello" is SKIPPED by default and answered with `REQUEST_ASSIST` |
| `language` | every hour | 24 | `preferredLanguageCode=fr-CA` produces French |
| `model_override` | every hour | 24 | `generationSpec.modelId` accepted |
| `image_generation` | every 4 h | 6 | image tool returns a file, download is plausible |
| `video_generation` | every 8 h | 3 | video tool returns a file (minutes-long stream) |
| `deep_research` | every 12 h | 4 | plan + "Start Research" produce a `RESEARCH_REPORT` |
| **total** | | **~781/day** | about 4.9x one Standard licence (160/day), about 24% of a 20-licence pool |

Other profiles: `probe` (only `probe` + `control_plane`, 288 queries/day) and
`full` (every fast check every run, about 3,500 queries/day - enough to
exhaust a 20-licence Standard pool and lock real users out until midnight PT;
use deliberately). Set the profile with `deploy.sh start 24 <profile>`.

Cadence is slot based (`slot = unix_time // 300`), so a missed run does not
shift the rotation and the report can list exactly which 5-minute slots have
no record.

## What is recorded

One JSON object per run in `runs/YYYY-MM-DD/HHMMSS_<tier>_<slot>.json`:

- run metadata: slot, scheduled vs actual start (`late_ms`), duration, caller
  identity, image sha, profile, campaign id;
- every API call: verb, path, HTTP status, latency, time to first byte, time
  to first decoded chunk, bytes, chunk count, `answer.state`,
  `assistSkippedReasons`, **`assistToken`** (what Google support asks for),
  session, text head, thought chars, generated files, planner functionCalls,
  grounding reference count, normalised error (kind / code / status /
  message / is_quota), redacted request body, response excerpt;
- every check: pass/fail, failed assertions, observations (non-critical
  facts such as "planner routed to the agent"), notes.

Mid-stream `{"error":...}` chunks, `answer.state == FAILED`, timeouts,
connection drops and non-JSON bodies are all classified separately
(chapter 9 / gotcha 9), and anything that looks like quota
(`429`, `RESOURCE_EXHAUSTED`, "quota" in the message) is flagged so the report
can say exactly when the pool ran out.

Every session a check creates is deleted at the end of the check
(`cleanup_delete_session` observation), so the SA's history does not grow
by 300 sessions a day; one-shot calls use `isSessionLess: true`.

## The report artifact

`python -m soak report` (the hourly `ge-soak-report` job, or
`deploy.sh report <label>`) writes to `reports/<label>/`:

| File | Contents |
|---|---|
| `report.md` | headline table (runs, calls, Assistant queries vs 160 and vs the pool, quota errors, probe availability, latency percentiles), queries per Pacific day, scheduler punctuality, per-check pass rates + observations, per-verb latency, hourly timeline, error catalogue with sample run ids and assistTokens |
| `report.json` | the same as data |
| `calls.csv` | one row per API call (open in Sheets to chart latency over the day) |
| `runs.csv`, `checks.csv` | one row per run / per check execution |

The window defaults to the campaign (`campaign.json` in the bucket); pass
`--start/--end` or `--window-hours` to override.

## Quota context

Per Google's [quotas and overages](https://docs.cloud.google.com/gemini/enterprise/docs/quotas-and-overages)
page, Assistant queries are a **licence feature quota pooled per project and
location**: Standard 160/day per licence, Plus 200, Frontline 40, reset at
midnight Pacific. The Discovery Engine technical quota ("Assist requests on
Assistants") is separate: 600/min/project by default. `SOAK_LICENSE_LIMIT`,
`SOAK_LICENSE_COUNT` and `SOAK_LICENSE_EDITION` feed the comparison in the
report; the values are not enforced by the harness.

## Local use

```bash
uv venv --python 3.12 .venv && .venv/bin/pip install -r soak/requirements.txt
make soak-local                                   # full fast tier once, results in soak/out/
cd soak && ../.venv/bin/python -m soak --local out report --window-hours 2 --no-upload --out out/report-local
cd soak && ../.venv/bin/python -m soak --local out run --tier heavy --only image_generation --ignore-campaign
```

Local runs use your gcloud ADC (so they count as *you*); on a corporate
machine export the TLS bundle variables from chapter 2 first.

## Layout

```
soak/
  deploy.sh          provision / build / deploy / start / stop / status / report / destroy
  Dockerfile         python:3.12-slim, context = repo root
  cloudbuild.yaml    Cloud Build recipe (tags image with the git sha)
  requirements.txt   requests, google-auth, tzdata
  soak/
    config.py        env-driven settings (.env names + SOAK_* fixtures)
    http.py          instrumented calls -> CallRecord (uses the guide's stream decoder)
    checks.py        the checks, their cadence and assertions
    runner.py        one scheduled execution -> runs/<date>/<file>.json
    report.py        aggregation + markdown/json/csv rendering
    storage.py       GCS via the JSON API, or a local directory
```
