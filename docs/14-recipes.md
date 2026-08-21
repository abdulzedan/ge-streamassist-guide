# 14. End-to-end recipes

Composed flows for common financial-services integration patterns. Each step
maps to a snippet you can run as-is.

## Recipe A — Document review copilot (upload → interrogate → audit trail)

```bash
cd snippets/curl
# 1. upload the document; "-" creates the session
UP=$(./15-upload-context-file.sh ~/loan-package.pdf)
SID=$(echo "$UP" | jq -r '.session' | awk -F/ '{print $NF}')
FID=$(echo "$UP" | jq -r '.fileId')

# 2. interrogate it — repeat with different questions, same session/fileId
./16-query-with-files.sh "$SID" "$FID" "List missing signatures and stale dates."
./16-query-with-files.sh "$SID" "$FID" "Summarize covenant terms as a table."

# 3. audit trail: the full turn history is stored on the session
./05-session-crud.sh get "$SID" | jq '.turns[].query.text'
```

## Recipe B — Compliance check via a pinned high-code agent

```bash
./06-list-agents.sh                          # find your compliance agent's ID
./08-invoke-specific-agent.sh <AGENT_ID> \
  "Run compliance checks on package #4711 and list any KYC flags."
# confirm the agent actually ran:
./08-invoke-specific-agent.sh <AGENT_ID> "..." \
  | jq '.[-1].answer.diagnosticInfo.plannerSteps[]?.planStep.parts[]?.functionCall.functionName'
```

If routing must be deterministic (straight-through processing), use the
native A2A line instead:

```bash
./24-a2a-message-stream.sh <AGENT_ID> "Audit package #4711."
```

## Recipe C — Morning market brief (deep research, unattended)

```bash
PLAN=$(./09-deep-research-plan.sh "Overnight moves in USD rates and IG credit; implications for our book")
SID=<session id printed by step 1>
./10-deep-research-execute.sh "$SID" > research.json          # runs minutes
jq -r '[ .[] | .answer.replies[]?
         | select(.groundedContent.contentMetadata.contentKind == "RESEARCH_REPORT")
         | .groundedContent.content.text // empty ] | join("")' research.json > report.md
# audio summary, if produced:
AFID=$(jq -r '[ .[] | .answer.replies[]?.groundedContent.content.file
                | select(.mimeType == "audio/mp3") | .fileId ][0]' research.json)
./17-download-session-file.sh "$SID" "$AFID" brief.mp3
```

## Recipe D — Grounded Q&A restricted to one repository

```bash
# e.g. only the policies data store, only documents tagged "2026"
./12-datastore-grounding.sh <DATA_STORE_ID> "What changed in the trading policy?"
# tighten further inside the snippet with:  "filter": "year: ANY(\"2026\")"
```

## Recipe E — Chart generation for a report

```bash
./13-image-generation.sh "clean line chart: 5-year treasury yield trend, minimalist"
./17-download-session-file.sh <SESSION_ID> <FILE_ID> chart.png
```

## Production checklist

- [ ] Parse the stream per chapter 9 (thoughts filtered, mid-stream errors handled, empty-text SUCCEEDED handled)
- [ ] Session strategy decided (persist per user? `isSessionLess` for one-shots?)
- [ ] Agent routing verified via `plannerSteps`, not assumed
- [ ] `REQUEST_ASSIST` set for programmatic traffic that may look like chit-chat
- [ ] Read timeouts ≥ 5 min for research/media calls
- [ ] fileIds persisted at upload time (listFiles quirk)
- [ ] Caller identity chosen deliberately (ACL-aware grounding)
- [ ] `assistToken` logged for supportability
- [ ] Quota alerting on the Discovery Engine API
