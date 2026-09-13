# 8. Files

Context files belong to sessions. They cover user uploads and generated image,
video and audio files.

## upload

`addContextFile` is available on `v1`, `v1beta` and `v1alpha`.

```text
POST {engine}/sessions/{session}:addContextFile
```

```json
{
  "fileName": "portfolio-memo.txt",
  "mimeType": "text/plain",
  "fileContents": "<base64>"
}
```

Use `-` as the session ID to create a session. Keep the returned `session` and
`fileId`.

## query

File selection is currently `v1alpha`:

```json
{
  "query": {"text": "Summarize the attached memo."},
  "session": "<upload session>",
  "fileIds": ["<file id>"]
}
```

The session must match the upload session. An empty query is accepted when
`fileIds` is present.

## list

`GET {session}:listSessionFileMetadata` is `v1alpha` only. The response array
is `fileMetadata[]`. Useful fields include `fileId`, `name`, `mimeType`,
`byteSize`, `tokenCount`, `selected`, `usedInConversation`, `uploadTime` and
`originalSourceType`.

## download

`downloadFile` works on the stable API:

```text
GET {session}:downloadFile?fileId={file-id}&alt=media
```

Use `alt=media` and follow redirects. The 2026-09-13 check uploaded a file,
listed it through `v1alpha`, downloaded it through `v1` and compared the bytes.

Generated media returns a `content.file` reference. Download it from the
session that produced it.
