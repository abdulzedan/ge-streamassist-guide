"""Instrumented HTTP layer: every API call becomes a CallRecord.

Reuses the guide client's incremental JSON-array decoder so the soak exercises
exactly the parsing path documented in chapter 9.
"""

from __future__ import annotations

import codecs
import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests
import requests

try:  # container layout: /app/ge_streamassist.py
    from ge_streamassist import _iter_json_array
except ImportError:  # repo layout: snippets/python/ge_streamassist.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "snippets" / "python"))
    from ge_streamassist import _iter_json_array

from .config import Config

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# Verbs that consume the per-license "Assistant queries" feature quota.
ASSIST_QUERY_VERBS = {"streamAssist", "assist", "a2a.message:stream"}


def utcnow_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int((time.time() % 1) * 1000):03d}Z"


class Auth:
    """Application Default Credentials: metadata server on Cloud Run, gcloud ADC locally."""

    def __init__(self) -> None:
        self._creds, self.adc_project = google.auth.default(scopes=_SCOPES)

    def token(self) -> str:
        if not self._creds.valid:
            self._creds.refresh(google.auth.transport.requests.Request())
        return self._creds.token

    def identity(self) -> str:
        email = getattr(self._creds, "service_account_email", None)
        if email and email != "default":
            return email
        if email == "default":  # metadata server: resolve the real email
            try:
                r = requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
                    headers={"Metadata-Flavor": "Google"}, timeout=2,
                )
                if r.ok:
                    return r.text.strip()
            except requests.RequestException:
                pass
            return "cloud-run-default-sa"
        return "user-adc"


@dataclass
class CallError:
    kind: str                     # http | stream_error | answer_failed | timeout | connection | parse | client
    code: int | None = None       # HTTP status or google.rpc code
    status: str | None = None     # e.g. RESOURCE_EXHAUSTED
    message: str = ""
    is_quota: bool = False

    def to_dict(self) -> dict:
        return {"kind": self.kind, "code": self.code, "status": self.status,
                "message": self.message[:600], "is_quota": self.is_quota}


@dataclass
class CallRecord:
    check: str
    verb: str
    method: str
    path: str
    api_version: str
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = ""
    status: int | None = None
    ok: bool = False
    latency_ms: int | None = None
    ttfb_ms: int | None = None          # headers received
    first_chunk_ms: int | None = None   # first decoded stream object
    bytes: int = 0
    chunks: int = 0
    assist_query: bool = False
    # answer-level facts (streamAssist / assist / a2a)
    answer_state: str | None = None
    skipped_reasons: list[str] = field(default_factory=list)
    assist_token: str | None = None
    session: str | None = None
    text: str = ""
    thought_chars: int = 0
    files: list[dict] = field(default_factory=list)
    planner_calls: list[str] = field(default_factory=list)
    tool_results: list[str] = field(default_factory=list)
    reply_agents: list[str] = field(default_factory=list)
    grounding_refs: int = 0
    content_kinds: list[str] = field(default_factory=list)
    a2a_roles: list[str] = field(default_factory=list)
    meta_text: str = field(default="", repr=False)
    error: CallError | None = None
    retry_after: str | None = None
    response_excerpt: Any = None        # small: JSON excerpt or raw text head
    request_excerpt: Any = None
    json: Any = field(default=None, repr=False)   # parsed body for non-stream calls (not serialized in full)

    @property
    def session_id(self) -> str | None:
        return self.session.rsplit("/", 1)[-1] if self.session else None

    def to_dict(self) -> dict:
        d = {
            "call_id": self.call_id, "check": self.check, "verb": self.verb, "method": self.method,
            "path": self.path, "api_version": self.api_version, "started_at": self.started_at,
            "status": self.status, "ok": self.ok, "latency_ms": self.latency_ms, "ttfb_ms": self.ttfb_ms,
            "first_chunk_ms": self.first_chunk_ms, "bytes": self.bytes, "chunks": self.chunks,
            "assist_query": self.assist_query, "answer_state": self.answer_state,
            "skipped_reasons": self.skipped_reasons, "assist_token": self.assist_token,
            "session": self.session, "text_chars": len(self.text), "text_head": self.text[:300],
            "thought_chars": self.thought_chars, "files": self.files, "planner_calls": self.planner_calls,
            "tool_results": self.tool_results, "reply_agents": sorted(set(self.reply_agents)), "grounding_refs": self.grounding_refs,
            "content_kinds": sorted(set(self.content_kinds)), "a2a_roles": sorted(set(self.a2a_roles)),
            "error": self.error.to_dict() if self.error else None, "retry_after": self.retry_after,
            "response_excerpt": self.response_excerpt, "request_excerpt": self.request_excerpt,
        }
        return d


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _quota_like(code: int | None, status: str | None, message: str) -> bool:
    msg = (message or "").lower()
    return code == 429 or status == "RESOURCE_EXHAUSTED" or "quota" in msg or "rate limit" in msg


def _parse_google_error(payload: Any) -> CallError | None:
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        e = payload["error"]
        code = e.get("code")
        status = e.get("status")
        message = str(e.get("message", ""))
        return CallError("http", code, status, message, _quota_like(code, status, message))
    return None


def _excerpt(obj: Any, limit: int = 1500) -> Any:
    """A compact, JSON-safe excerpt of a response body for the run record."""
    if obj is None:
        return None
    if isinstance(obj, (bytes, bytearray)):
        return {"bytes": len(obj)}
    try:
        text = json.dumps(obj, default=str)
    except TypeError:
        text = str(obj)
    if len(text) <= limit:
        return obj
    return {"_truncated": True, "_chars": len(text), "head": text[:limit]}


def redact_request(body: Any) -> Any:
    if isinstance(body, dict):
        out = {}
        for k, v in body.items():
            if k == "fileContents":
                out[k] = f"<base64 {len(str(v))} chars>"
            else:
                out[k] = redact_request(v)
        return out
    if isinstance(body, list):
        return [redact_request(v) for v in body]
    return body


class _CountingResponse:
    """Duck-types requests.Response.iter_content for the guide's decoder while
    counting raw bytes and decoding UTF-8 incrementally (multi-byte characters
    can straddle chunk boundaries)."""

    def __init__(self, resp: requests.Response) -> None:
        self._resp = resp
        self.n = 0

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = True):
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        for raw in self._resp.iter_content(chunk_size=chunk_size, decode_unicode=False):
            if not raw:
                continue
            self.n += len(raw)
            text = decoder.decode(raw)
            if text:
                yield text
        tail = decoder.decode(b"", final=True)
        if tail:
            yield tail


class Api:
    """All API calls go through here so they are measured identically."""

    def __init__(self, cfg: Config, auth: Auth) -> None:
        self.cfg = cfg
        self.auth = auth
        self.calls: list[CallRecord] = []
        self._http = requests.Session()
        self.user_agent = f"ge-soak/{cfg.git_sha}"

    # -- plumbing -------------------------------------------------------

    def _headers(self, extra: dict | None = None) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.auth.token()}",
            "X-Goog-User-Project": self.cfg.project_id,
            "User-Agent": self.user_agent,
        }
        if extra:
            h.update(extra)
        return h

    def request(
        self,
        check: str,
        verb: str,
        method: str,
        path: str,
        *,
        version: str | None = None,
        json_body: Any = None,
        params: dict | None = None,
        timeout: tuple[float, float] = (10, 120),
        stream: bool = False,
        expect_bytes: bool = False,
        allow_redirects: bool = True,
    ) -> CallRecord:
        api_version = version or self.cfg.api_version
        rec = CallRecord(check=check, verb=verb, method=method, path=path, api_version=api_version,
                         started_at=utcnow_iso(), assist_query=verb in ASSIST_QUERY_VERBS,
                         request_excerpt=redact_request(json_body) if json_body is not None else None)
        self.calls.append(rec)
        url = self.cfg.url(path, api_version)
        t0 = time.perf_counter()
        try:
            resp = self._http.request(
                method, url, params=params, json=json_body, stream=True,
                headers=self._headers({"Content-Type": "application/json"} if json_body is not None else None),
                timeout=timeout, allow_redirects=allow_redirects,
            )
            rec.ttfb_ms = _ms(t0)
            rec.status = resp.status_code
            rec.retry_after = resp.headers.get("Retry-After")
            if resp.status_code >= 400:
                raw = resp.content
                rec.bytes = len(raw)
                rec.latency_ms = _ms(t0)
                err = None
                try:
                    payload = json.loads(raw.decode("utf-8", "replace"))
                    payload = payload[0] if isinstance(payload, list) and payload else payload
                    err = _parse_google_error(payload)
                    rec.response_excerpt = _excerpt(payload)
                except ValueError:
                    rec.response_excerpt = raw[:800].decode("utf-8", "replace")
                rec.error = err or CallError("http", resp.status_code, None, rec.response_excerpt if isinstance(rec.response_excerpt, str) else "",
                                             _quota_like(resp.status_code, None, ""))
                return rec
            if stream:
                self._consume_stream(rec, resp, t0)
            elif expect_bytes:
                raw = resp.content
                rec.bytes = len(raw)
                rec.json = raw
                rec.response_excerpt = {"bytes": len(raw), "content_type": resp.headers.get("Content-Type")}
                rec.ok = True
            else:
                raw = resp.content
                rec.bytes = len(raw)
                if raw.strip():
                    try:
                        rec.json = json.loads(raw.decode("utf-8", "replace"))
                    except ValueError:
                        rec.error = CallError("parse", resp.status_code, None, raw[:300].decode("utf-8", "replace"))
                        rec.response_excerpt = raw[:800].decode("utf-8", "replace")
                        rec.latency_ms = _ms(t0)
                        return rec
                else:
                    rec.json = {}
                err = _parse_google_error(rec.json)
                if err:
                    rec.error = err
                else:
                    rec.ok = True
                    if verb in ("assist",):
                        self._absorb_answer_chunk(rec, rec.json)
                        rec.ok = rec.error is None
                rec.response_excerpt = _excerpt(rec.json)
            rec.latency_ms = _ms(t0)
        except requests.exceptions.Timeout as exc:
            rec.latency_ms = _ms(t0)
            rec.error = CallError("timeout", None, None, f"{type(exc).__name__}: {exc}"[:300])
        except requests.exceptions.ConnectionError as exc:
            rec.latency_ms = _ms(t0)
            rec.error = CallError("connection", None, None, f"{type(exc).__name__}: {exc}"[:300])
        except requests.exceptions.RequestException as exc:
            rec.latency_ms = _ms(t0)
            rec.error = CallError("client", None, None, f"{type(exc).__name__}: {exc}"[:300])
        return rec

    # -- stream handling -----------------------------------------------

    def _consume_stream(self, rec: CallRecord, resp: requests.Response, t0: float) -> None:
        shim = _CountingResponse(resp)
        try:
            for obj in _iter_json_array(shim):  # type: ignore[arg-type]
                if rec.first_chunk_ms is None:
                    rec.first_chunk_ms = _ms(t0)
                rec.chunks += 1
                if rec.verb == "a2a.message:stream":
                    self._absorb_a2a_item(rec, obj)
                else:
                    self._absorb_answer_chunk(rec, obj)
        except requests.exceptions.ChunkedEncodingError as exc:
            rec.error = rec.error or CallError("connection", None, None, f"stream cut: {exc}"[:300])
        except requests.exceptions.Timeout as exc:
            rec.error = rec.error or CallError("timeout", None, None, f"mid-stream: {type(exc).__name__}: {exc}"[:300])
        except (ValueError, json.JSONDecodeError) as exc:
            rec.error = rec.error or CallError("parse", None, None, f"stream decode: {exc}"[:300])
        finally:
            rec.bytes = shim.n
            resp.close()
        if rec.verb == "a2a.message:stream" and not rec.text:
            rec.text = rec.meta_text
        if rec.error is None:
            if rec.answer_state == "FAILED":
                rec.error = CallError("answer_failed", None, None, "answer.state == FAILED")
            elif rec.chunks == 0:
                rec.error = CallError("parse", None, None, "empty stream (no JSON objects)")
            else:
                rec.ok = True

    def _absorb_answer_chunk(self, rec: CallRecord, chunk: Any) -> None:
        if not isinstance(chunk, dict):
            return
        if isinstance(chunk.get("error"), dict) and rec.error is None:
            e = chunk["error"]
            code, status, msg = e.get("code"), e.get("status"), str(e.get("message", ""))
            rec.error = CallError("stream_error", code, status, msg, _quota_like(code, status, msg))
            rec.response_excerpt = _excerpt(chunk)
        info = chunk.get("sessionInfo") or {}
        if info.get("session"):
            rec.session = info["session"]
        if chunk.get("assistToken"):
            rec.assist_token = chunk["assistToken"]
        answer = chunk.get("answer") or {}
        if answer.get("state"):
            rec.answer_state = answer["state"]
        rec.skipped_reasons.extend(answer.get("assistSkippedReasons", []))
        if answer.get("adkAuthor"):
            rec.reply_agents.append(f"adkAuthor:{answer['adkAuthor']}")
        for reply in answer.get("replies", []):
            if reply.get("agent"):
                rec.reply_agents.append(str(reply["agent"]))
            gc = reply.get("groundedContent") or {}
            content = gc.get("content") or {}
            if content.get("thought"):
                rec.thought_chars += len(content.get("text", ""))
            elif isinstance(content.get("text"), str):
                rec.text += content["text"]
            if "file" in content:
                rec.files.append(content["file"])
            kind = (gc.get("contentMetadata") or {}).get("contentKind")
            if kind:
                rec.content_kinds.append(kind)
            for key, value in gc.items():
                if key.endswith("GroundingMetadata") and isinstance(value, dict):
                    rec.grounding_refs += len(value.get("references", []) or []) + len(value.get("groundingChunks", []) or [])
                if key == "citationMetadata" and isinstance(value, dict):
                    rec.grounding_refs += len(value.get("citations", []) or [])
        for step in (answer.get("diagnosticInfo") or {}).get("plannerSteps", []) or []:
            for part in (step.get("planStep") or {}).get("parts", []) or []:
                fc = part.get("functionCall")
                if fc and fc.get("functionName"):
                    rec.planner_calls.append(fc["functionName"])
            for part in (step.get("toolStep") or {}).get("parts", []) or []:
                fr = part.get("functionResult")
                if fr and fr.get("functionName"):
                    rec.tool_results.append(fr["functionName"])

    def _absorb_a2a_item(self, rec: CallRecord, item: Any) -> None:
        if not isinstance(item, dict):
            return
        if isinstance(item.get("error"), dict) and rec.error is None:
            e = item["error"]
            code, status, msg = e.get("code"), e.get("status"), str(e.get("message", ""))
            rec.error = CallError("stream_error", code, status, msg, _quota_like(code, status, msg))
        msg = item.get("message") or {}
        if msg.get("role"):
            rec.a2a_roles.append(msg["role"])
        if msg.get("contextId"):
            rec.session = msg["contextId"]
        for part in msg.get("content", []) or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                rec.text += part["text"]
        meta = msg.get("metadata") or {}
        if meta:
            saved = rec.text
            rec.text = rec.meta_text
            self._absorb_answer_chunk(rec, meta)   # fills state/session/token/planner/thoughts
            rec.meta_text, rec.text = rec.text, saved
        task = item.get("task") or {}
        state = (task.get("status") or {}).get("state")
        if state:
            rec.answer_state = rec.answer_state or state

    # -- verbs -----------------------------------------------------------

    def stream_assist(self, check: str, body: dict, read_timeout: float = 300) -> CallRecord:
        return self.request(check, "streamAssist", "POST", f"{self.cfg.assistant_path}:streamAssist",
                            json_body=body, stream=True, timeout=(10, read_timeout))

    def assist(self, check: str, body: dict, read_timeout: float = 300) -> CallRecord:
        return self.request(check, "assist", "POST", f"{self.cfg.assistant_path}:assist",
                            json_body=body, timeout=(10, read_timeout))

    def a2a_message_stream(self, check: str, agent_id: str, text: str, read_timeout: float = 600) -> CallRecord:
        body = {"message": {"role": "ROLE_USER", "content": [{"text": text}],
                            "messageId": f"soak-{uuid.uuid4().hex[:10]}"}}
        return self.request(check, "a2a.message:stream", "POST",
                            f"{self.cfg.assistant_path}/agents/{agent_id}/a2a/v1/message:stream",
                            version="v1", json_body=body, stream=True, timeout=(10, read_timeout))

    def a2a_card(self, check: str, agent_id: str) -> CallRecord:
        return self.request(check, "a2a.card", "GET",
                            f"{self.cfg.assistant_path}/agents/{agent_id}/a2a/v1/card", version="v1")

    def get(self, check: str, verb: str, path: str, params: dict | None = None, version: str | None = None) -> CallRecord:
        return self.request(check, verb, "GET", path, params=params, version=version)

    def create_session(self, check: str, display_name: str) -> CallRecord:
        return self.request(check, "sessions.create", "POST", f"{self.cfg.engine_path}/sessions",
                            json_body={"displayName": display_name})

    def get_session(self, check: str, session_id: str) -> CallRecord:
        return self.get(check, "sessions.get", f"{self.cfg.engine_path}/sessions/{session_id}",
                        params={"includeAnswerDetails": "true"})

    def list_sessions(self, check: str, page_size: int = 10) -> CallRecord:
        return self.get(check, "sessions.list", f"{self.cfg.engine_path}/sessions",
                        params={"pageSize": page_size, "orderBy": "update_time desc"})

    def delete_session(self, check: str, session_id: str) -> CallRecord:
        return self.request(check, "sessions.delete", "DELETE", f"{self.cfg.engine_path}/sessions/{session_id}")

    def add_context_file(self, check: str, session: str, file_name: str, mime: str, b64: str) -> CallRecord:
        return self.request(check, "sessions.addContextFile", "POST",
                            f"{self.cfg.engine_path}/sessions/{session}:addContextFile",
                            json_body={"fileName": file_name, "mimeType": mime, "fileContents": b64},
                            timeout=(10, 300))

    def list_session_files(self, check: str, session_id: str) -> CallRecord:
        return self.get(check, "sessions.listSessionFileMetadata",
                        f"{self.cfg.engine_path}/sessions/{session_id}:listSessionFileMetadata")

    def download_file(self, check: str, session_id: str, file_id: str) -> CallRecord:
        return self.request(check, "sessions.downloadFile", "GET",
                            f"{self.cfg.engine_path}/sessions/{session_id}:downloadFile",
                            params={"fileId": file_id, "alt": "media"}, expect_bytes=True, timeout=(10, 300))

    def list_agents(self, check: str) -> CallRecord:
        return self.get(check, "agents.list", f"{self.cfg.assistant_path}/agents", params={"pageSize": 100})

    def get_agent(self, check: str, agent_id: str) -> CallRecord:
        return self.get(check, "agents.get", f"{self.cfg.assistant_path}/agents/{agent_id}")

    def get_assistant(self, check: str) -> CallRecord:
        return self.get(check, "assistants.get", self.cfg.assistant_path)

    def get_engine(self, check: str) -> CallRecord:
        return self.get(check, "engines.get", self.cfg.engine_path)
