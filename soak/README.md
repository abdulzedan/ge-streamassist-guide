# Stream Assist soak test

Cloud Scheduler triggers three Cloud Run Jobs:

```text
every 5 min  -> ge-soak-fast
every 4 h    -> ge-soak-heavy
hourly       -> ge-soak-report
                         -> gs://{bucket}/runs and reports
```

The jobs use one image built from `soak/Dockerfile`. They run under
`ge-soak@{project}.iam.gserviceaccount.com`; the target project and app come
from `.env`.

## commands

```bash
./soak/deploy.sh deploy
./soak/deploy.sh run fast
./soak/deploy.sh start 24 standard
./soak/deploy.sh status
./soak/deploy.sh report final
./soak/deploy.sh stop
./soak/deploy.sh destroy
```

`deploy` creates or updates cloud resources and leaves schedulers paused.
`destroy` removes the jobs and schedulers but keeps the bucket and service
account.

## standard profile

| Check | Cadence | What it checks |
|---|---|---|
| control plane | every run | agent, assistant, engine and session reads |
| probe | 5 min | stable `v1` Stream Assist, text and session cleanup |
| multi-turn | 30 min | two turns, recall, get and delete |
| native A2A | 30 min | card plus text or an auth/confirmation handoff |
| web grounding | 30 min | web tool response and reference observation |
| data-store grounding | 30 min | one selected store |
| file round trip | hourly | upload, list, query, download and byte comparison |
| Assist | hourly | non-streaming response |
| skip mode | hourly | classifier and alpha override |
| language/model | hourly | metadata and model override |
| image | 4 h | file response and download |
| video | 8 h | file response and download |
| Deep Research | 12 h | plan, execute and report marker |

The standard schedule makes about 637 `streamAssist`/`assist` calls per day.
This is an estimate from scheduled calls, not a billing counter. Configure
`SOAK_LICENSE_COUNT` before comparing with a pool; the default is zero.

The `full` profile runs every fast check every five minutes and every heavy
check every four hours. It can create more than 3,000 candidate calls per day.

## evidence and privacy

Each run records method, API version, timing, byte/chunk counts, answer state,
skip reasons, support token, session, file metadata, content kinds, routing
markers, handoff flags and sanitized errors. Request and response values are
reduced to structure and character counts before storage.

Every created session has a cleanup observation. A failed critical assertion
now makes the Cloud Run Job fail.

## local

```bash
python3 -m venv .venv
.venv/bin/pip install -r soak/requirements.txt
cd soak
set -a; . ../.env; set +a
../.venv/bin/python -m soak --local out run --tier fast --all --ignore-campaign
../.venv/bin/python -m soak --local out report --window-hours 2 --no-upload --out out/report-local
```

Quota notes and the completed campaign summary are in
[chapter 15](../docs/15-soak-test.md).
