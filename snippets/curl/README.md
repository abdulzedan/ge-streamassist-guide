# curl snippets

Each script is standalone: it sources [`common.sh`](common.sh) (which loads
`../../.env` and mints a token) and makes one focused call. Run any of them
from anywhere; most take their inputs as arguments.

| # | Script | Capability |
|---|---|---|
| 01 | `01-basic-stream-assist.sh` | simplest streamAssist call |
| 02 | `02-extract-answer-text.sh` | jq extraction of the answer text |
| 03 | `03-create-session.sh` | explicit session creation |
| 04 | `04-multi-turn-session.sh` | two-turn conversation |
| 05 | `05-session-crud.sh` | list / get / pin / delete sessions |
| 06 | `06-list-agents.sh` | agent inventory with types & states |
| 07 | `07-get-agent.sh` | one agent's full definition |
| 08 | `08-invoke-specific-agent.sh` | invoke any agent via agentsSpec |
| 09 | `09-deep-research-plan.sh` | Deep Research step 1 (plan) |
| 10 | `10-deep-research-execute.sh` | Deep Research step 2 (execute) |
| 11 | `11-web-grounding.sh` | web-grounded answer |
| 12 | `12-datastore-grounding.sh` | data-store-restricted answer |
| 13 | `13-image-generation.sh` | image generation |
| 14 | `14-video-generation.sh` | video generation |
| 15 | `15-upload-context-file.sh` | file upload (addContextFile) |
| 16 | `16-query-with-files.sh` | Q&A over uploaded files |
| 17 | `17-download-session-file.sh` | download session files |
| 18 | `18-non-streaming-assist.sh` | non-streaming :assist |
| 19 | `19-assist-skipping-mode.sh` | chit-chat classifier override |
| 20 | `20-language-and-user-metadata.sh` | language fallback + time zone |
| 21 | `21-generation-spec-model.sh` | per-request model override |
| 22 | `22-get-assistant.sh` | assistant configuration |
| 23 | `23-a2a-get-card.sh` | native A2A agent card |
| 24 | `24-a2a-message-stream.sh` | native A2A direct message |
| 25 | `25-list-data-stores.sh` | connected data stores |
| 26 | `26-diagnose-routing.sh` | plannerSteps routing verdict |
| 27 | `27-list-session-file-metadata.sh` | list session context files (the working verb) |
