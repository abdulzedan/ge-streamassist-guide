# 7. Deep Research

Deep Research is a Made-by-Google agent registered on the app with the fixed
agent ID **`deep_research`**. Via API it is GA **with allowlist** — if step 1
below fails for you, request allowlisting through your Google account team.
(Made-by-Google agents are not available in Frontline edition.)

## The two-step flow

Deep Research never runs immediately: step 1 returns a research **plan**, and
the research only starts when you approve it **in the same session**.

### Step 1 — request the plan ([snippet 09](../snippets/curl/09-deep-research-plan.sh))

```json
{
  "query":   { "text": "Current trends in agentic AI adoption in retail banking" },
  "session": ".../sessions/-",
  "agentsSpec": { "agentSpecs": [ { "agentId": "deep_research" } ] },
  "toolsSpec": { "webGroundingSpec": {} }
}
```

Response: a normal short stream whose text is the plan (a reply may carry
`contentMetadata.contentKind: "RESEARCH_PLAN"`). **Save
`sessionInfo.session`.**
Captured: [`outputs/09-deep-research-plan.json`](../outputs/09-deep-research-plan.json).

You can also ground the research on your data stores by adding
`vertexAiSearchSpec` to `toolsSpec` in both steps.

### Step 2 — approve and run ([snippet 10](../snippets/curl/10-deep-research-execute.sh))

Same body, same session, and a confirmation query...the documented phrase is
`"Start Research"` (natural-language approvals like "the plan looks good,
proceed" also work). You can also request plan edits instead; the agent
returns a revised plan.

**This call streams for the entire research run — typically 5–20 minutes.**
Configure your HTTP client accordingly (snippet 10 sets `--max-time 1800`).

### What the execution stream contains (verified live)

Replies are tagged via `groundedContent.contentMetadata.contentKind`, in
roughly this order:

| contentKind | Meaning |
|---|---|
| `RESEARCH_PLAN` | (step 1 / revised plans) |
| `RESEARCH_QUESTION` | each sub-question the agent decided to investigate (has a `contentId`) |
| `RESEARCH_ANSWER` | streamed findings per question, grounded with `textGroundingMetadata` |
| `RESEARCH_REPORT` | the final consolidated report text |
| `RESEARCH_AUDIO_SUMMARY` | an audio summary; the reply content is `{"file": {"fileId": "...", "mimeType": "audio/mp3"}}` |

A real run against a live app produced 8 research questions, a ~72,000
character report and an mp3 audio summary
(structure excerpt: [`outputs/10-deep-research-execute.excerpt.json`](../outputs/10-deep-research-execute.excerpt.json)).

Download the audio summary with
[`17-download-session-file.sh`](../snippets/curl/17-download-session-file.sh)
using the session from step 1 and the audio `fileId`.

## Python

[`04_deep_research.py`](../snippets/python/examples/04_deep_research.py) runs
the full flow and prints contentKind transitions as progress markers.

## Caveats

- **Do not** send step 2 without `agentsSpec` pinning `deep_research` — the
  approval would be answered by the base assistant and the research never
  starts.
- The stream can stay silent for minutes between chunks. Don't set idle
  timeouts below ~5 minutes; if the connection drops you can re-attach by
  polling the session (`GET session?includeAnswerDetails=true`), but the
  simplest robust pattern is a generous read timeout.
- Each research question re-grounds; expect the run to consume noticeably
  more quota than regular assist calls.
- The report arrives as many `RESEARCH_ANSWER`/`RESEARCH_REPORT` fragments —
  concatenate text per `contentKind` (and use `contentId` to group
  question/answer pairs).
