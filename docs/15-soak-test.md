# 15. Reliability soak test (24 h, every 5 minutes, from Cloud Run)

Chapters 1-14 prove that each capability works *once*. This chapter is about
how the API behaves over a day of unattended traffic from a headless
identity: availability, latency distribution, quota accounting and whether
the documented behaviours (routing, skip classifier, file round trips,
session cleanup) stay stable.

The harness lives in [`soak/`](../soak/README.md). In one paragraph: Cloud
Scheduler triggers a Cloud Run Job every five minutes; the job runs the
availability probe plus a rotating subset of the capability checks (the
same requests as the curl snippets, issued through the guide's Python
stream decoder), records every call with its `assistToken`, latency and a
normalised error, and writes one JSON record per run to a bucket. An hourly
job turns the records into `report.md` / `report.json` / CSVs.

## Why the numbers in the report look the way they do

- **Assistant queries vs 160.** 160 is the *per-licence* daily allowance of
  the Standard edition (Plus 200, Frontline 40), pooled across all licences
  in the project and location and reset at midnight Pacific
  ([quotas and overages](https://docs.cloud.google.com/gemini/enterprise/docs/quotas-and-overages)).
  A headless service account with no licence was able to call `streamAssist`
  (verified 2026-09-09), so its traffic presumably draws from the same pool.
  The default profile issues about 781 queries a day: roughly five licences'
  worth, a quarter of a 20-licence Standard pool. The `full` profile issues
  about 3,500 and will lock real users out of a 20-licence pool until
  midnight PT.
- **Three counters, three verbs.** The report counts `streamAssist`, the
  undocumented `:assist` and native `a2a/v1/message:stream` as Assistant
  queries. Whether all three really decrement the licence pool is not
  documented; the report shows them separately in the per-verb table so you
  can reconcile against the console's Usage & Spending page.
- **Technical quota is not the limit.** "Assist requests on Assistants" is
  600 per minute per project by default; one probe every five minutes never
  gets near it. A `429`/`RESOURCE_EXHAUSTED` in the report is therefore the
  licence pool, not the API rate limit.
- **Routing is an observation, not a pass/fail.** `agentsSpec` scopes rather
  than forces (gotcha 2); the check passes when the pinned call SUCCEEDED
  with text and *additionally* reports how often `plannerSteps` shows a
  functionCall. A routing rate well below 100% for a domain-matched query is
  the finding.
- **Missed slots are scheduler facts.** Cadence is keyed on
  `unix_time // 300`, so the report lists the exact five-minute slots with no
  run record and the p95 start delay after the mark.

## Reading the artifact

Start with the headline table, then the per-check table (failed assertions
name the exact step: `turn2_recalls_code`, `uploaded_file_listed`,
`report_content_kind`...), then the error catalogue - every row carries a
sample run id and `assistToken` for a support ticket. `calls.csv` has one
row per call for charting latency over the day.

Findings from the first full campaign will be recorded here and in
[`outputs/soak/`](../outputs/) once the 24-hour window has closed.
