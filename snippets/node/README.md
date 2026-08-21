# Node.js client

Zero-dependency (Node 18+): `fetch` + `gcloud` for the token.

```bash
node example.mjs "What can you do?"
```

[`ge-streamassist.mjs`](ge-streamassist.mjs) exports `GEClient` with an async
generator `streamAssist({ query, session, agentId, fileIds, toolsSpec,
forceAssist })` that decodes the streamed JSON array incrementally
(brace-counting parser — no buffering of the whole response).

For production, replace the `gcloud` token shell-out with
`google-auth-library`.

Corporate machines with TLS interception:
`export NODE_EXTRA_CA_CERTS=/etc/ssl/cert.pem`.
