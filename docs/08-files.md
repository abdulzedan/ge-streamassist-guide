# 8. Files: upload, query, download

Session **context files** cover both directions: files you upload for the
assistant to read, and files the assistant generates (images, videos, audio
summaries).

## Upload: `:addContextFile` ([snippet 15](../snippets/curl/15-upload-context-file.sh))

```
POST {version}/{ENGINE}/sessions/{SESSION_ID}:addContextFile
{
  "fileName":     "portfolio-memo.txt",
  "mimeType":     "text/plain",
  "fileContents": "<base64>"
}
```

- `SESSION_ID` may be `-` → creates a new session and uploads in one call.
- Response (captured: [`outputs/15-add-context-file.json`](../outputs/15-add-context-file.json)):

```json
{
  "session":   "projects/000000000000/.../sessions/381265427528616266",
  "fileId":    "381265427528617709",
  "tokenCount": "51",
  "mimeType":  "text/plain",
  "byteCount": "154",
  "fileName":  "portfolio-memo.txt"
}
```

- Preview/pre-GA feature; needs `discoveryengine.sessions.addContextFile`.
- `tokenCount` (deprecated but still returned) is a useful sanity check that
  the file was actually parsed.
- Content travels base64-inside-JSON — fine for documents; for very large
  media an undocumented multipart endpoint exists
  (`POST https://{host}/upload/{version}/{session}:uploadFile` with
  `metadata={"name":"<session>"}` + `file=@...` parts, returns `{"fileId"}`),
  verified working but unsupported — prefer `addContextFile`.

## Query the file ([snippet 16](../snippets/curl/16-query-with-files.sh))

```json
{
  "query":   { "text": "What is the delinquency rate in the attached memo?" },
  "session": "<the session the file was uploaded to>",
  "fileIds": [ "<fileId>" ]
}
```

- `fileIds` is **v1alpha-only**.
- An **empty query is allowed** when `fileIds` is present (the assistant
  summarizes/analyzes the files).
- The session must match the upload session — fileIds don't cross sessions.
- Captured: [`outputs/16-query-with-files.json`](../outputs/16-query-with-files.json).

## Download: `:downloadFile` ([snippet 17](../snippets/curl/17-download-session-file.sh))

```
GET {version}/{ENGINE}/sessions/{SESSION_ID}:downloadFile?fileId={FILE_ID}&alt=media
```

Two mandatory quirks, both verified:

1. **`alt=media` is required.** Without it you get an empty `200` with
   `Content-Type: application/json` and zero bytes.
2. **The response is a `302` redirect** to a signed URL — `curl -L` (or
   `allow_redirects=True`) is required; the raw response body is a redirect
   stub, not your file.

Where do fileIds come from?

| Source | Where the ID appears |
|---|---|
| your upload | `addContextFile` response `.fileId` |
| generated image/video/audio | reply chunk `content.file.fileId` |
| Drive/document references in queries | `queryPart.*Reference.fileId` (output only) |

## Listing files: use `:listSessionFileMetadata`, not `:listFiles`

Two similar-looking verbs exist; only one is for you:

```
GET {session}:listSessionFileMetadata     ✅ works — AssistantService surface
GET {session}:listFiles                   ❌ 403 "Session is not owned by the
                                             provided user" for API-created
                                             sessions (unreleased collaborative-
                                             projects surface — not a real
                                             ownership problem)
GET {session}/files                       ❌ 404 (documented in the discovery
                                             doc, not routed live)
```

`:listSessionFileMetadata` works headless with the same credentials that
created the session and returns `fileId`, `name`, `mimeType`, `byteSize`,
`tokenCount`, `quotaPercentage` (session file-quota consumption) and
`selected` per file. Snippet:
[`27-list-session-file-metadata.sh`](../snippets/curl/27-list-session-file-metadata.sh).

Still good hygiene: persist `fileId`s from upload responses and
generated-file replies rather than re-listing on every turn.

## MIME types

Uploads accepted include text, PDF, office documents and images (same set as
the UI attachment feature). `mimeType` may be omitted when the file name has a
recognizable extension; supplying it avoids server-side guessing.
