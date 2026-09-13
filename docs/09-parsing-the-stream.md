# 9. Parsing the stream

This chapter follows the current schema and live response shapes in
[`outputs/`](../outputs/).

## Wire format: a streamed JSON array

`streamAssist` responds `200` with `Content-Type: application/json` and a body
that is one **JSON array** of `StreamAssistResponse` objects, streamed
incrementally:

```
[ { ...chunk 1... }
,
{ ...chunk 2... }
,
{ ...chunk N... }
]
```

It is **not** Server-Sent Events (`data:` lines) and **not** NDJSON. Options:

- **Buffer-then-parse** (simplest): read the whole body, `json.loads` /
  `jq`. You lose token-by-token streaming — fine for scripts. All curl
  snippets in this repo do this.
- **Incremental decode** (real streaming): repeatedly strip a leading `[`/`,`,
  then `raw_decode` one object off the buffer. The repo's Python client
  implements this (`_iter_json_array` in
  [`ge_streamassist.py`](../snippets/python/ge_streamassist.py)).

## Chunk anatomy

```jsonc
{
  "answer": {
    "state": "IN_PROGRESS",              // then SUCCEEDED | FAILED | SKIPPED | CANCELLED
    "replies": [ {
      "groundedContent": {
        "content": {
          "role": "model",
          "text": "…fragment…",          // append fragments in order
          "thought": true                 // OPTIONAL: reasoning, not answer text
        },
        "contentMetadata": { "contentKind": "RESEARCH_PLAN", "contentId": "…" },
        "textGroundingMetadata": { "references": [...], "segments": [...] },
        "citationMetadata": { "citations": [...] }
      },
      "replyId": "…",                     // same replyId = same logical reply
      "createTime": "…"
    } ],
    "assistSkippedReasons": [...],        // when state == SKIPPED
    "diagnosticInfo": { "plannerSteps": [...] },  // optional planner detail
    "name": ".../assistAnswers/{id}"      // only on the final chunk
  },
  "sessionInfo": { "session": "…", "queryId": "…" },
  "assistToken": "…"                      // quote this in support tickets
}
```

## The assembly algorithm

1. For each chunk, iterate `answer.replies[]`.
2. Take `groundedContent.content`:
   - `thought == true` → reasoning trace. Keep out of the user-visible answer.
   - `text` present → append to the answer buffer (fragments are pre-ordered).
   - `file` present → a generated artifact: `{fileId, mimeType}` — download
     separately.
   - `inlineData` present → small binary payload (base64) delivered inline.
   - `executableCode` / `codeExecutionResult` → code-interpreter traffic.
3. Watch `answer.state`: `IN_PROGRESS` → keep reading; anything else is final.
4. Read `sessionInfo.session` from the final object on `v1`.

Handle these cases:

- **Empty content objects**: `{"content": {"role": "model"}}` with no text —
  skip them.
- **Empty groundedContent** `{}` and metadata-only replies
  (`textGroundingMetadata` without `content`) — skip unless you want
  citations.
- **`SUCCEEDED` with zero text** — legal (some managed agents; see chapter 5).
- **Errors arrive mid-stream with HTTP 200**: a chunk can be
  `{"error": {"code": 400, "status": "FAILED_PRECONDITION", …}}` after an
  earlier `{"answer": {"state": "FAILED"}}` chunk. Checking only the HTTP
  status catches nothing — inspect chunks.
- `sessionInfo` may be missing from some chunks — read it where present.

## jq one-liners

```bash
# answer text only (drop thoughts)
jq -r '[ .[] | .answer.replies[]? | .groundedContent.content
         | select(. != null and .thought != true) | .text // empty ] | join("")'

# final state + skip reasons
jq -r '.[-1].answer | "\(.state) \(.assistSkippedReasons // [] | join(","))"'

# generated files
jq '[ .[] | .answer.replies[]? | .groundedContent.content.file | select(. != null) ]'

# session to continue with
jq -er '[ .[] | .sessionInfo.session // empty ] | last'

# routing trace: which agent actually ran
jq '.[-1].answer.diagnosticInfo.plannerSteps // "no planner trace"'
```

## HTTP client settings

- Use a streaming client and allow several quiet minutes for Deep Research or
  video generation.
