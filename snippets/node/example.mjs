// Streamed answer to stdout. Reads config from ../../.env.
//   node example.mjs "your question"

import { readFileSync } from "node:fs";
import { GEClient } from "./ge-streamassist.mjs";

const env = Object.fromEntries(
  readFileSync(new URL("../../.env", import.meta.url), "utf8")
    .split("\n")
    .map((l) => l.replace(/^export\s+/, "").trim())
    .filter((l) => l && !l.startsWith("#") && l.includes("="))
    .map((l) => {
      const [k, ...v] = l.split("=");
      return [k, v.join("=").replace(/^"|"$/g, "")];
    })
);

const ge = new GEClient({
  projectId: env.PROJECT_ID,
  appId: env.APP_ID,
  location: env.LOCATION ?? "global",
});

const query = process.argv[2] ?? "Explain dollar-cost averaging in two sentences.";

for await (const chunk of ge.streamAssist({ query })) {
  for (const reply of chunk.answer?.replies ?? []) {
    const content = reply.groundedContent?.content;
    if (content?.text && !content.thought) process.stdout.write(content.text);
  }
}
process.stdout.write("\n");
