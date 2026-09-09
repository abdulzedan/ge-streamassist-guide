# 12. Caveats & gotchas

Every item below was either reproduced live against a real app (marked ✓) or
comes from official docs / credible field reports (marked ⓘ). This is the
chapter to read before writing production code.

## Request routing & agents

1. ✓ **No `agentsSpec` ⇒ base assistant.** The single most common mistake:
   omit `agentsSpec` and the orchestrator answers with the default assistant —
   your custom agent's prompt don't apply in this scenario.
2. ✓ **`agentsSpec` scopes, it doesn't force.** Meta questions ("what do you
   do?") may still be answered by the orchestrator even with an agent pinned.
   Verify actual routing via `answer.diagnosticInfo.plannerSteps` (look for the
   `functionCall` step). For guaranteed delivery use the native A2A surface
   (chapter 11).
3. ✓ **Bad/disabled/private agent IDs do NOT error.** streamAssist silently
   behaves as if the agent weren't there (or, with `REQUEST_ASSIST`, fails with
   a mid-stream `FAILED_PRECONDITION`). No 404 exists on this path — check
   agent state via `06-list-agents.sh` first.
4. ✓ **Greetings get SKIPPED.** The chit-chat classifier returns
   `state: SKIPPED`, reason `NON_ASSIST_SEEKING_QUERY_IGNORED` — for "hello",
   even with a valid agent pinned. Your "smoke test with hi" will fail while
   real queries work. Override: `"assistSkippingMode": "REQUEST_ASSIST"`.
5. ⓘ **agentsSpec silently stripped on some projects (field report,
   March 2026).** REST calls invoking *user-created* agents were ignored while
   the same body worked from the UI; Cloud Logging showed the block removed.
   Fix required a Google support case ("product engineering made internal
   project changes"). If routing never happens and plannerSteps show no
   functionCall, open a case. (discuss.google.dev thread 336726,
   google-cloud-python #16019)
6. ✓ **`agentsConfig`/`answerGenerationMode` exist but 
   `agentsConfig.agent` requires the **project-number** resource name
   (project ID → `Invalid agent name`), and results were inconsistent in
   testing. Prefer `agentsSpec`.
7. ✓ **Managed/no-code agents may return SUCCEEDED with zero text.**
   Data-Insights-style agents answer only their query types. Handle empty
   answers; don't equate SUCCEEDED with "has text".

## Streaming & responses

8. ✓ **The stream is a JSON array, not SSE/NDJSON.** `[ {...} , {...} ]`
   delivered incrementally. SSE parsers see garbage; naive `json.loads` per
   line fails. See chapter 9.
9. ✓ **Errors arrive mid-stream with HTTP 200.** A `{"error": {...}}` chunk
   can follow successful chunks. Status-code-only error handling misses them.
10. ✓ **Thought fragments are interleaved.** `content.thought: true` items are
    reasoning, not answer — filter them or your users see the model thinking.
11. ✓ **Fragments repeat metadata.** `sessionInfo`/`assistToken` on nearly
    every chunk; replies with empty `content`, empty `groundedContent`, or
    metadata-only (grounding) entries are normal — skip defensively.
12. ✓ **Resource names switch to project NUMBER.** You send project ID; every
    returned resource name contains the number. Don't string-match on the
    path you sent.

## Versions & API surface

13. ✓ **The workhorse fields are v1alpha-only** (`agentsSpec`, `fileIds`,
    `assistSkippingMode`, `isSessionLess`) and several (`agentsSpec`,
    `fileIds`, `assistSkippingMode`) are **absent even from the v1alpha public
    discovery document** — generated clients (Python/Ruby/etc.) won't have
    them. Call REST directly.
14. ✓ **`:assist` (non-streaming) is undocumented.** Works today on v1alpha;
    could change without notice. Prefer streamAssist.
15. ⓘ **Docs mix versions in their own examples** (v1 template, v1alpha for
    fileIds). When something 400s with "unknown field", check the version.
16. ⓘ **Doc URLs churn.** `cloud.google.com/gemini/enterprise/docs/*` now
    redirects to `docs.cloud.google.com/...`; older page slugs
    (`invoke-agent-streamassist`, `invoke-agent-a2a`) are gone. The live
    equivalents: `get-answers-from-streamassist`, `research-assistant`,
    `register-and-manage-an-adk-agent`, `register-and-manage-an-a2a-agent`.

## Sessions, files, memory

17. ✓ **Use `{session}:listSessionFileMetadata` to list session files —
    NOT `:listFiles`.** `:listFiles` belongs to an unreleased
    collaborative-projects surface and returns a misleading
    `403 "Session is not owned by the provided user"` for API-created
    sessions regardless of caller; `GET {session}/files` (as documented in
    the discovery doc) 404s. `:listSessionFileMetadata` works headless with
    the creating credentials (snippet 27).
18. ✓ **Downloads need `alt=media` AND `-L`.** Without `alt=media`: empty 200.
    Without following the 302 redirect: a JSON stub instead of bytes.
19. ✓ **`fileIds` don't cross sessions.** Query must use the session the file
    was uploaded to.
20. ✓ **Cross-session user memory exists.** A fresh session can reference
    facts learned in earlier sessions of the same user ("as someone in fixed
    income…"). Relevant for testing isolation AND for compliance reviews —
    deleting a session isn't a memory wipe.
21. ✓ **Sessions created by your backend appear in the user's UI history**
    (auto-titled from the first query). Use `isSessionLess: true` for
    throwaway calls.

## Language, models, tools

22. ✓ **`preferredLanguageCode` is a fallback, not a switch.** A French
    query got a French answer; an English query with `fr-CA` stayed English.
    To force a language, instruct it in the prompt.
23. ✓ **Web grounding spec is silently inert** when the assistant-level
    `webGroundingType` doesn't allow it. Check `22-get-assistant.sh`.
24. ⓘ **`dataStoreSpecs.dataStore` requires the project number** per the API
    reference (ID observed working — don't depend on it).
25. ✓ **Generated media is never inline** (file references only) — plan a
    second call to download; and budget for long stream-silences during
    video/Deep Research runs (>5 min idle timeouts).

## Deep Research

26. ✓ **Two calls, one session, agent pinned both times.** Forgetting
    `agentsSpec` on the "Start Research" call sends your approval to the base
    assistant and nothing happens.
27. ⓘ **API access is allowlisted** (GA-with-allowlist; not in Frontline).
28. ✓ **Runs are long** (minutes to tens of minutes) and quota-hungry —
    each research question re-grounds.

## Operations

29. ✓ **`X-Goog-User-Project` matters** — its absence causes
    misleading `CONSUMER_INVALID` / `USER_PROJECT_DENIED` errors.
30. ✓ **The app "Name" in the UI is not the GCP project ID.** Resolve the
    hosting project first (`./scripts/discover.sh`); querying the wrong
    project yields `Project not found or deleted`.
31. ⓘ **Identity drives grounding.** ACL-aware connectors (Drive, SharePoint,
    Gmail) return the *caller's* documents. A service account will not see
    what your test user sees.
32. ✓ **Keep `assistToken`.** It's the request correlation ID Google support
    asks for.
33. ✓ **Failure shapes for bad agents are inconsistent.** With
    `REQUEST_ASSIST`, an inaccessible PRIVATE agent produced
    `FAILED` + mid-stream error, while a nonexistent ID sometimes produced a
    normal `SUCCEEDED` base-assistant answer. Treat "wrong agent" as
    undetectable from status alone — verify via `plannerSteps`
    (snippet 26).
34. ✓ **Corporate TLS interception breaks Python/Node but not curl.** See the
    workaround in [chapter 2](02-authentication.md#corporate-tls-interception).
