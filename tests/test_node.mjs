import assert from "node:assert/strict";
import test from "node:test";

import { GEClient } from "../snippets/node/ge-streamassist.mjs";

const encoder = new TextEncoder();

function response(chunks, status = 200) {
  const body = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { status });
}

function client() {
  const ge = new GEClient({ projectId: "project", appId: "app" });
  ge.token = () => "test-token";
  return ge;
}

test("Node client parses chunk boundaries and serializes query text", async () => {
  const originalFetch = globalThis.fetch;
  let request;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return response([
      '[{"answer":{"state":"IN_',
      'PROGRESS"}},',
      '{"answer":{"state":"SUCCEEDED"}}]'
    ]);
  };
  try {
    const query = 'quotes " backslash \\ and\nnewline';
    const chunks = [];
    for await (const chunk of client().streamAssist({ query, isSessionLess: true })) {
      chunks.push(chunk);
    }
    assert.equal(chunks.length, 2);
    assert.match(request.url, /\/v1alpha\//);
    assert.equal(JSON.parse(request.options.body).query.text, query);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Node client rejects a truncated stream", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => response(['[{"answer":{"state":"IN_PROGRESS"}}']);
  try {
    await assert.rejects(async () => {
      for await (const _ of client().streamAssist({ query: "hello" })) {
        // drain the generator
      }
    }, /closing JSON-array bracket/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Node client rejects an error object inside HTTP 200", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => response(['[{"error":{"status":"FAILED_PRECONDITION"}}]']);
  try {
    await assert.rejects(async () => {
      for await (const _ of client().streamAssist({ query: "hello" })) {
        // drain the generator
      }
    }, /FAILED_PRECONDITION/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
