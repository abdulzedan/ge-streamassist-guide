# 7. Deep Research

Deep Research uses the fixed agent ID `deep_research`. API access is GA with
allowlisting and is unavailable in Frontline editions.

## 1. get the plan

```json
{
  "query": {"text": "Current trends in agentic AI adoption in retail banking"},
  "session": "projects/.../engines/.../sessions/-",
  "agentsSpec": {"agentSpecs": [{"agentId": "deep_research"}]},
  "toolsSpec": {"webGroundingSpec": {}}
}
```

Save the final `sessionInfo.session`. The plan may be marked
`RESEARCH_PLAN`.

## 2. approve it

Send `Start Research` in the same session and include the same `agentsSpec`.
Keep any data-store grounding spec on both calls.

The execution takes minutes and may be quiet between chunks. The guide uses a
30-minute client timeout.

| `contentKind` | Content |
|---|---|
| `RESEARCH_QUESTION` | generated sub-question |
| `RESEARCH_ANSWER` | grounded findings |
| `RESEARCH_REPORT` | final report |
| `RESEARCH_AUDIO_SUMMARY` | downloadable audio file, when produced |

Concatenate text by `contentKind`; use `contentId` when pairing questions and
answers. Download files with [snippet 17](../snippets/curl/17-download-session-file.sh).

The 2026-09-13 live run completed with a report, grounding references and an
MP3 summary. No size or duration from that single run is treated as a service
guarantee.
