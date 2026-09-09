"""Capability checks. Each check issues a few instrumented API calls and
records assertions; `critical=False` assertions are observations that are
reported as rates but do not fail the check (e.g. whether the planner really
routed to the pinned agent - gotcha 2)."""

from __future__ import annotations

import base64
import random
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from .config import Config
from .http import Api, CallRecord, utcnow_iso


@dataclass
class Assertion:
    name: str
    ok: bool
    critical: bool = True
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "critical": self.critical, "detail": self.detail[:300]}


@dataclass
class CheckResult:
    name: str
    tier: str
    started_at: str
    duration_ms: int = 0
    ok: bool = False
    assertions: list[Assertion] = field(default_factory=list)
    call_ids: list[str] = field(default_factory=list)
    notes: dict = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name, "tier": self.tier, "started_at": self.started_at,
            "duration_ms": self.duration_ms, "ok": self.ok, "error": self.error,
            "failed": [a.name for a in self.assertions if a.critical and not a.ok],
            "observations": {a.name: a.ok for a in self.assertions if not a.critical},
            "assertions": [a.to_dict() for a in self.assertions],
            "call_ids": self.call_ids, "notes": self.notes,
        }


@dataclass
class Ctx:
    cfg: Config
    api: Api
    run_id: str
    tier: str
    slot: int
    heavy_index: int
    project_number: str | None = None

    @property
    def engine(self) -> str:
        return self.cfg.engine_path

    def new_session_ref(self) -> str:
        return f"{self.engine}/sessions/-"

    def cleanup(self, check: str, res: CheckResult, session: str | None) -> None:
        """Delete a session the check created so the SA's history stays clean."""
        if not session:
            res.assertions.append(Assertion("cleanup_delete_session", False, False, "no session to delete"))
            return
        sid = session.rsplit("/", 1)[-1]
        rec = self.api.delete_session(check, sid)
        res.assertions.append(Assertion("cleanup_delete_session", rec.ok, False, _err(rec)))


# -- assertion helpers ---------------------------------------------------

def _err(rec: CallRecord) -> str:
    if rec.error:
        return f"{rec.error.kind} {rec.error.code or ''} {rec.error.status or ''} {rec.error.message}".strip()
    return f"http {rec.status}"


def a_http(res: CheckResult, rec: CallRecord, name: str = "http_ok", critical: bool = True) -> bool:
    res.assertions.append(Assertion(name, rec.ok, critical, _err(rec)))
    return rec.ok


def a_state(res: CheckResult, rec: CallRecord, expected: str = "SUCCEEDED", name: str | None = None, critical: bool = True) -> bool:
    ok = rec.answer_state == expected
    res.assertions.append(Assertion(name or f"state_{expected.lower()}", ok, critical,
                                    f"state={rec.answer_state} skipped={rec.skipped_reasons}"))
    return ok


def a_text(res: CheckResult, rec: CallRecord, name: str = "has_text", critical: bool = True) -> bool:
    ok = bool(rec.text.strip())
    res.assertions.append(Assertion(name, ok, critical, f"{len(rec.text)} chars"))
    return ok


def a_contains(res: CheckResult, rec: CallRecord, needle: str, name: str, critical: bool = True) -> bool:
    ok = needle.lower() in rec.text.lower()
    res.assertions.append(Assertion(name, ok, critical, f"looking for {needle!r} in {rec.text[:120]!r}"))
    return ok


def a_answer(res: CheckResult, rec: CallRecord, prefix: str = "") -> bool:
    """The standard trio for an assist call: transport ok, SUCCEEDED, non-empty text."""
    p = f"{prefix}_" if prefix else ""
    ok = a_http(res, rec, f"{p}http_ok")
    ok = a_state(res, rec, name=f"{p}state_succeeded") and ok
    ok = a_text(res, rec, f"{p}has_text") and ok
    return ok


_OK_QUERY = "Reply with exactly the single word: OK"


def _sessionless(query: str, **extra) -> dict:
    body = {"query": {"text": query}, "isSessionLess": True, "assistSkippingMode": "REQUEST_ASSIST"}
    body.update(extra)
    return body


# -- fast tier -----------------------------------------------------------

def c_control_plane(ctx: Ctx, res: CheckResult) -> None:
    api, cfg = ctx.api, ctx.cfg
    agents = api.list_agents(res.name)
    if a_http(res, agents, "agents_list_ok"):
        items = (agents.json or {}).get("agents", [])
        by_id = {a["name"].rsplit("/", 1)[-1]: a for a in items}
        states: dict[str, int] = {}
        for a in items:
            states[a.get("state", "?")] = states.get(a.get("state", "?"), 0) + 1
        res.notes["agents_total"] = len(items)
        res.notes["agents_by_state"] = states
        for label, aid in (("adk", cfg.adk_agent_id), ("a2a", cfg.a2a_agent_id)):
            a = by_id.get(aid)
            res.assertions.append(Assertion(
                f"fixture_{label}_agent_enabled", bool(a) and a.get("state") == "ENABLED", False,
                f"{aid}: {a.get('state') if a else 'missing'} {a.get('displayName', '') if a else ''}"))
    agent = api.get_agent(res.name, cfg.adk_agent_id)
    a_http(res, agent, "agents_get_ok")
    assistant = api.get_assistant(res.name)
    if a_http(res, assistant, "assistants_get_ok"):
        res.notes["web_grounding_type"] = (assistant.json or {}).get("webGroundingType")
    engine = api.get_engine(res.name)
    if a_http(res, engine, "engines_get_ok"):
        body = engine.json or {}
        res.notes["data_stores"] = len(body.get("dataStoreIds", []))
        m = re.match(r"projects/(\d+)/", body.get("name", ""))
        if m:
            ctx.project_number = m.group(1)
            res.notes["project_number"] = m.group(1)
    sessions = api.list_sessions(res.name, page_size=50)
    if a_http(res, sessions, "sessions_list_ok"):
        res.notes["sessions_visible"] = len((sessions.json or {}).get("sessions", []))


def c_probe(ctx: Ctx, res: CheckResult) -> None:
    rec = ctx.api.stream_assist(res.name, _sessionless(_OK_QUERY), read_timeout=120)
    a_answer(res, rec)
    a_contains(res, rec, "ok", "says_ok", critical=False)
    res.notes["ttfb_ms"] = rec.ttfb_ms
    res.notes["first_chunk_ms"] = rec.first_chunk_ms


def c_multiturn(ctx: Ctx, res: CheckResult) -> None:
    code = f"SOAK-{ctx.slot % 100000}-{ctx.run_id[-4:].upper()}"
    t1 = ctx.api.stream_assist(res.name, {
        "query": {"text": f"My reference code is {code}. Acknowledge it in one short sentence."},
        "session": ctx.new_session_ref(), "assistSkippingMode": "REQUEST_ASSIST"})
    ok = a_answer(res, t1, "turn1")
    res.assertions.append(Assertion("turn1_session_returned", bool(t1.session), True, t1.session or ""))
    if not (ok and t1.session):
        return
    t2 = ctx.api.stream_assist(res.name, {
        "query": {"text": "What is my reference code? Reply with the code only."},
        "session": t1.session, "assistSkippingMode": "REQUEST_ASSIST"})
    a_answer(res, t2, "turn2")
    a_contains(res, t2, code, "turn2_recalls_code")
    get = ctx.api.get_session(res.name, t1.session_id or "")
    if a_http(res, get, "sessions_get_ok"):
        turns = (get.json or {}).get("turns", [])
        res.assertions.append(Assertion("session_has_two_turns", len(turns) >= 2, False, f"{len(turns)} turns"))
    ctx.cleanup(res.name, res, t1.session)


def _pinned_agent(ctx: Ctx, res: CheckResult, agent_id: str, query: str, timeout: float) -> None:
    rec = ctx.api.stream_assist(res.name, {
        "query": {"text": query}, "session": ctx.new_session_ref(),
        "agentsSpec": {"agentSpecs": [{"agentId": agent_id}]},
        "assistSkippingMode": "REQUEST_ASSIST"}, read_timeout=timeout)
    a_answer(res, rec)
    routed = bool(rec.planner_calls) or any(agent_id in a for a in rec.reply_agents)
    res.assertions.append(Assertion("routed_to_agent", routed, False,
                                    f"planner functionCalls={rec.planner_calls[:5]} replyAgents={sorted(set(rec.reply_agents))[:5]}"))
    res.notes["planner_calls"] = rec.planner_calls[:10]
    res.notes["reply_agents"] = sorted(set(rec.reply_agents))[:10]
    ctx.cleanup(res.name, res, rec.session)


def c_agent_adk(ctx: Ctx, res: CheckResult) -> None:
    _pinned_agent(ctx, res, ctx.cfg.adk_agent_id,
                  "Review this mortgage file: borrower income 95,000, loan amount 420,000, LTV 85%, "
                  "credit score 700, 30-year fixed. List the key underwriting risks in bullet points.", 300)


def c_agent_a2a(ctx: Ctx, res: CheckResult) -> None:
    _pinned_agent(ctx, res, ctx.cfg.a2a_agent_id,
                  "Run a compliance check on loan package #4711 and list any KYC flags.", 300)


def c_a2a_native(ctx: Ctx, res: CheckResult) -> None:
    card = ctx.api.a2a_card(res.name, ctx.cfg.adk_agent_id)
    a_http(res, card, "card_ok")
    rec = ctx.api.a2a_message_stream(res.name, ctx.cfg.adk_agent_id,
                                     "In one sentence, what can you help me with?", read_timeout=300)
    a_http(res, rec)
    res.assertions.append(Assertion("agent_role_seen", "ROLE_AGENT" in rec.a2a_roles, True, f"roles={sorted(set(rec.a2a_roles))}"))
    a_text(res, rec)
    res.notes["answer_state"] = rec.answer_state
    ctx.cleanup(res.name, res, rec.session)


def c_web_grounding(ctx: Ctx, res: CheckResult) -> None:
    rec = ctx.api.stream_assist(res.name, _sessionless(
        "What is today's date, and what is one major business news headline from today? Answer in two sentences.",
        toolsSpec={"webGroundingSpec": {}}), read_timeout=300)
    a_answer(res, rec)
    res.assertions.append(Assertion("grounding_refs_present", rec.grounding_refs > 0, False, f"{rec.grounding_refs} refs"))


def c_datastore_grounding(ctx: Ctx, res: CheckResult) -> None:
    cfg = ctx.cfg
    if ctx.project_number and not cfg.project_number:
        object.__setattr__(cfg, "project_number", ctx.project_number)
    rec = ctx.api.stream_assist(res.name, _sessionless(
        "Using only the connected documentation, summarize what the architecture documentation covers in two sentences.",
        toolsSpec={"vertexAiSearchSpec": {"dataStoreSpecs": [{"dataStore": cfg.data_store_path(cfg.data_store_id)}]}}),
        read_timeout=300)
    a_answer(res, rec)
    res.assertions.append(Assertion("grounding_refs_present", rec.grounding_refs > 0, False, f"{rec.grounding_refs} refs"))


def c_file_roundtrip(ctx: Ctx, res: CheckResult) -> None:
    magic = str(random.randint(1000, 9999))
    memo = f"Soak test memo {ctx.run_id}.\nThe magic number is {magic}.\n".encode()
    up = ctx.api.add_context_file(res.name, "-", f"soak-memo-{ctx.run_id}.txt", "text/plain",
                                  base64.b64encode(memo).decode())
    if not a_http(res, up, "upload_ok"):
        return
    body = up.json or {}
    session, file_id = body.get("session"), body.get("fileId")
    res.assertions.append(Assertion("upload_returns_ids", bool(session and file_id), True, f"session={session} fileId={file_id}"))
    if not (session and file_id):
        return
    sid = session.rsplit("/", 1)[-1]
    listing = ctx.api.list_session_files(res.name, sid)
    if a_http(res, listing, "list_files_ok"):
        ids = [f.get("fileId") for f in (listing.json or {}).get("fileMetadata", [])]
        res.assertions.append(Assertion("uploaded_file_listed", file_id in ids, True, f"listed={ids}"))
    q = ctx.api.stream_assist(res.name, {
        "query": {"text": "What is the magic number in the attached memo? Reply with the number only."},
        "session": session, "fileIds": [file_id], "assistSkippingMode": "REQUEST_ASSIST"})
    a_answer(res, q, "query")
    a_contains(res, q, magic, "answer_has_magic_number")
    dl = ctx.api.download_file(res.name, sid, file_id)
    if a_http(res, dl, "download_ok"):
        res.assertions.append(Assertion("download_bytes_match", dl.json == memo, False, f"{dl.bytes} bytes vs {len(memo)} uploaded"))
    ctx.cleanup(res.name, res, session)


def c_assist_nonstreaming(ctx: Ctx, res: CheckResult) -> None:
    rec = ctx.api.assist(res.name, {"query": {"text": _OK_QUERY}}, read_timeout=120)
    a_answer(res, rec)
    name = ((rec.json or {}).get("answer") or {}).get("name", "") if isinstance(rec.json, dict) else ""
    m = re.search(r"/sessions/(\d+)/", name)
    ctx.cleanup(res.name, res, f"{ctx.engine}/sessions/{m.group(1)}" if m else None)


def c_skip_mode(ctx: Ctx, res: CheckResult) -> None:
    plain = ctx.api.stream_assist(res.name, {"query": {"text": "hello"}, "isSessionLess": True}, read_timeout=120)
    a_http(res, plain, "default_http_ok")
    res.assertions.append(Assertion("classifier_skips_greeting", plain.answer_state == "SKIPPED", False,
                                    f"state={plain.answer_state} reasons={plain.skipped_reasons}"))
    forced = ctx.api.stream_assist(res.name, _sessionless("hello"), read_timeout=120)
    a_answer(res, forced, "request_assist")


_FRENCH = re.compile(r"\b(les|des|est|une|et|pour|dans|avec)\b", re.IGNORECASE)


def c_language(ctx: Ctx, res: CheckResult) -> None:
    rec = ctx.api.stream_assist(res.name, _sessionless(
        "Quels sont les avantages des achats périodiques par sommes fixes? Réponds en deux phrases.",
        userMetadata={"preferredLanguageCode": "fr-CA", "timeZone": "America/Toronto"}), read_timeout=180)
    a_answer(res, rec)
    res.assertions.append(Assertion("answer_in_french", len(_FRENCH.findall(rec.text)) >= 3, False, rec.text[:100]))


def c_model_override(ctx: Ctx, res: CheckResult) -> None:
    rec = ctx.api.stream_assist(res.name, _sessionless(_OK_QUERY, generationSpec={"modelId": ctx.cfg.model_id}), read_timeout=120)
    a_answer(res, rec)
    res.notes["model_id"] = ctx.cfg.model_id


# -- heavy tier ----------------------------------------------------------

def _generate_media(ctx: Ctx, res: CheckResult, spec_key: str, prompt: str, mime_prefix: str, min_bytes: int, timeout: float) -> None:
    rec = ctx.api.stream_assist(res.name, {
        "query": {"text": prompt}, "session": ctx.new_session_ref(), "toolsSpec": {spec_key: {}}}, read_timeout=timeout)
    a_http(res, rec)
    a_state(res, rec)
    media = [f for f in rec.files if str(f.get("mimeType", "")).startswith(mime_prefix)]
    res.assertions.append(Assertion("media_file_returned", bool(media), True, f"files={rec.files[:3]}"))
    res.notes["files"] = rec.files[:3]
    if media and rec.session_id:
        dl = ctx.api.download_file(res.name, rec.session_id, media[0]["fileId"])
        if a_http(res, dl, "download_ok"):
            res.assertions.append(Assertion("download_size_plausible", dl.bytes >= min_bytes, True, f"{dl.bytes} bytes"))
            res.notes["download_bytes"] = dl.bytes
    ctx.cleanup(res.name, res, rec.session)


def c_image_generation(ctx: Ctx, res: CheckResult) -> None:
    _generate_media(ctx, res, "imageGenerationSpec",
                    "Generate an image: a simple solid blue circle centered on a white background.",
                    "image/", 1000, 600)


def c_video_generation(ctx: Ctx, res: CheckResult) -> None:
    _generate_media(ctx, res, "videoGenerationSpec",
                    "Generate a video: a calm ocean at sunrise, gentle waves.", "video/", 10000, 1500)


def c_deep_research(ctx: Ctx, res: CheckResult) -> None:
    pin = {"agentsSpec": {"agentSpecs": [{"agentId": "deep_research"}]}, "toolsSpec": {"webGroundingSpec": {}}}
    plan = ctx.api.stream_assist(res.name, {
        "query": {"text": "Current trends in agentic AI adoption in retail banking"},
        "session": ctx.new_session_ref(), **pin}, read_timeout=600)
    ok = a_answer(res, plan, "plan")
    res.assertions.append(Assertion("plan_content_kind", "RESEARCH_PLAN" in plan.content_kinds, False, f"kinds={sorted(set(plan.content_kinds))}"))
    if not (ok and plan.session):
        return
    run = ctx.api.stream_assist(res.name, {"query": {"text": "Start Research"}, "session": plan.session, **pin}, read_timeout=2400)
    a_answer(res, run, "execute")
    res.assertions.append(Assertion("report_content_kind", "RESEARCH_REPORT" in run.content_kinds, True, f"kinds={sorted(set(run.content_kinds))}"))
    res.notes["report_chars"] = len(run.text)
    res.notes["files"] = run.files[:3]
    ctx.cleanup(res.name, res, plan.session)


# -- registry ------------------------------------------------------------

@dataclass(frozen=True)
class CheckSpec:
    name: str
    fn: Callable[[Ctx, CheckResult], None]
    tier: str
    every: int          # run when index % every == offset
    offset: int
    assist_queries: int  # expected Assistant-query quota consumption per execution
    description: str


FAST_CHECKS: list[CheckSpec] = [
    CheckSpec("control_plane", c_control_plane, "fast", 1, 0, 0, "agents.list/get, assistants.get, engines.get, sessions.list"),
    CheckSpec("probe", c_probe, "fast", 1, 0, 1, "sessionless streamAssist expecting 'OK' (core availability probe)"),
    CheckSpec("multiturn", c_multiturn, "fast", 6, 0, 2, "two turns in one session, recall a reference code, sessions.get, delete"),
    CheckSpec("agent_adk", c_agent_adk, "fast", 6, 1, 1, "agentsSpec pinned to the ADK agent; routing verified via plannerSteps"),
    CheckSpec("agent_a2a", c_agent_a2a, "fast", 6, 2, 1, "agentsSpec pinned to the A2A agent; routing verified via plannerSteps"),
    CheckSpec("a2a_native", c_a2a_native, "fast", 6, 3, 1, "native a2a/v1 card + message:stream to the ADK agent"),
    CheckSpec("web_grounding", c_web_grounding, "fast", 6, 4, 1, "toolsSpec.webGroundingSpec"),
    CheckSpec("datastore_grounding", c_datastore_grounding, "fast", 6, 5, 1, "toolsSpec.vertexAiSearchSpec on one data store"),
    CheckSpec("file_roundtrip", c_file_roundtrip, "fast", 12, 6, 1, "addContextFile, listSessionFileMetadata, fileIds query, downloadFile"),
    CheckSpec("assist_nonstreaming", c_assist_nonstreaming, "fast", 12, 0, 1, "undocumented :assist"),
    CheckSpec("skip_mode", c_skip_mode, "fast", 12, 3, 2, "'hello' with and without assistSkippingMode=REQUEST_ASSIST"),
    CheckSpec("language", c_language, "fast", 12, 9, 1, "userMetadata.preferredLanguageCode=fr-CA"),
    CheckSpec("model_override", c_model_override, "fast", 12, 11, 1, "generationSpec.modelId"),
]

HEAVY_CHECKS: list[CheckSpec] = [
    CheckSpec("image_generation", c_image_generation, "heavy", 1, 0, 1, "imageGenerationSpec + downloadFile"),
    CheckSpec("video_generation", c_video_generation, "heavy", 2, 0, 1, "videoGenerationSpec + downloadFile"),
    CheckSpec("deep_research", c_deep_research, "heavy", 3, 1, 2, "deep_research plan + Start Research"),
]

PROFILES = ("standard", "full", "probe")


def due(spec: CheckSpec, index: int, profile: str) -> bool:
    if profile == "probe":
        return spec.name in ("probe", "control_plane")
    if profile == "full":
        return True
    return index % spec.every == spec.offset % spec.every


def run_check(spec: CheckSpec, ctx: Ctx) -> CheckResult:
    res = CheckResult(name=spec.name, tier=spec.tier, started_at=utcnow_iso())
    first = len(ctx.api.calls)
    t0 = time.perf_counter()
    try:
        spec.fn(ctx, res)
    except Exception as exc:  # a bug in a check must not kill the run
        res.error = f"{type(exc).__name__}: {exc}"[:500]
        res.assertions.append(Assertion("no_exception", False, True, res.error))
    res.duration_ms = int((time.perf_counter() - t0) * 1000)
    res.call_ids = [c.call_id for c in ctx.api.calls[first:]]
    res.ok = res.error is None and all(a.ok for a in res.assertions if a.critical)
    return res
