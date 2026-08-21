// Minimal Node.js (18+) client for the Gemini Enterprise Stream Assist API.
// Zero dependencies: uses fetch + gcloud for the token.
//
//   import { GEClient } from "./ge-streamassist.mjs";
//   const ge = new GEClient({ projectId, appId });
//   for await (const chunk of ge.streamAssist({ query: "Hello" })) { ... }

import { execFileSync } from "node:child_process";

export class GEClient {
  constructor({ projectId, appId, location = "global", assistantId = "default_assistant", apiVersion = "v1alpha" }) {
    this.projectId = projectId;
    this.appId = appId;
    this.location = location;
    this.assistantId = assistantId;
    this.apiVersion = apiVersion;
  }

  get host() {
    return this.location === "global"
      ? "discoveryengine.googleapis.com"
      : `${this.location}-discoveryengine.googleapis.com`;
  }

  get enginePath() {
    return `projects/${this.projectId}/locations/${this.location}/collections/default_collection/engines/${this.appId}`;
  }

  get assistantPath() {
    return `${this.enginePath}/assistants/${this.assistantId}`;
  }

  token() {
    // Simplest possible auth for samples. In production use google-auth-library.
    return execFileSync("gcloud", ["auth", "print-access-token"], { encoding: "utf8" }).trim();
  }

  headers() {
    return {
      Authorization: `Bearer ${this.token()}`,
      "Content-Type": "application/json",
      "X-Goog-User-Project": this.projectId,
    };
  }

  /**
   * POST :streamAssist and yield response chunks as they arrive.
   * The wire format is a streamed JSON array — decoded incrementally.
   */
  async *streamAssist({ query, session, agentId, fileIds, toolsSpec, forceAssist }) {
    const body = {};
    if (query) body.query = { text: query };
    if (session) {
      body.session = session.includes("/") ? session : `${this.enginePath}/sessions/${session}`;
    }
    if (agentId) body.agentsSpec = { agentSpecs: [{ agentId }] };
    if (fileIds) body.fileIds = fileIds;
    if (toolsSpec) body.toolsSpec = toolsSpec;
    if (forceAssist) body.assistSkippingMode = "REQUEST_ASSIST";

    const resp = await fetch(`https://${this.host}/${this.apiVersion}/${this.assistantPath}:streamAssist`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`streamAssist HTTP ${resp.status}: ${await resp.text()}`);

    let buf = "";
    const decoder = new TextDecoder();
    for await (const bytes of resp.body) {
      buf += decoder.decode(bytes, { stream: true });
      while (true) {
        buf = buf.replace(/^[\s\[,]+/, "");
        if (!buf || buf[0] === "]") break;
        const obj = tryParsePrefix(buf);
        if (!obj) break; // need more bytes
        yield obj.value;
        buf = buf.slice(obj.length);
      }
    }
  }
}

// Parse one JSON object off the front of the buffer by brace counting
// (strings/escapes handled), returning {value, length} or null.
function tryParsePrefix(s) {
  let depth = 0, inStr = false, esc = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (esc) { esc = false; continue; }
    if (c === "\\") { if (inStr) esc = true; continue; }
    if (c === '"') { inStr = !inStr; continue; }
    if (inStr) continue;
    if (c === "{") depth++;
    else if (c === "}") {
      depth--;
      if (depth === 0) {
        return { value: JSON.parse(s.slice(0, i + 1)), length: i + 1 };
      }
    }
  }
  return null;
}
