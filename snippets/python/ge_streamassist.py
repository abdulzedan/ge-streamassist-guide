"""Minimal client for the Gemini Enterprise Stream Assist API.

Only dependencies: `requests` and `google-auth` (see requirements.txt).

The one non-obvious piece is stream parsing: streamAssist responds with a
single JSON *array* streamed over HTTP — `[ {chunk}, {chunk}, ... ]` — not
SSE and not newline-delimited JSON. `stream_assist()` decodes chunks
incrementally as bytes arrive, so you get tokens as they are generated
instead of waiting for the full response.
"""

from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional

import google.auth
import google.auth.transport.requests
import requests

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


@dataclass
class GEClient:
    """Client bound to one Gemini Enterprise app (engine)."""

    project_id: str
    app_id: str
    location: str = "global"
    assistant_id: str = "default_assistant"
    api_version: str = "v1alpha"
    _creds: Any = field(default=None, repr=False)

    # -- plumbing ------------------------------------------------------

    @property
    def host(self) -> str:
        if self.location == "global":
            return "discoveryengine.googleapis.com"
        return f"{self.location}-discoveryengine.googleapis.com"

    @property
    def engine_path(self) -> str:
        return (
            f"projects/{self.project_id}/locations/{self.location}"
            f"/collections/default_collection/engines/{self.app_id}"
        )

    @property
    def assistant_path(self) -> str:
        return f"{self.engine_path}/assistants/{self.assistant_id}"

    def _token(self) -> str:
        if self._creds is None:
            self._creds, _ = google.auth.default(scopes=_SCOPES)
        if not self._creds.valid:
            self._creds.refresh(google.auth.transport.requests.Request())
        return self._creds.token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.project_id,
        }

    def _url(self, path_and_verb: str) -> str:
        return f"https://{self.host}/{self.api_version}/{path_and_verb}"

    # -- streamAssist --------------------------------------------------

    def stream_assist(
        self,
        query: Optional[str] = None,
        session: Optional[str] = None,
        agent_id: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        tools_spec: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        force_assist: bool = False,
        user_metadata: Optional[Dict[str, str]] = None,
        timeout: int = 1800,
    ) -> Generator[Dict[str, Any], None, None]:
        """Call :streamAssist and yield StreamAssistResponse chunks as dicts.

        session: full session resource name, a bare session ID, or "-" to
        create a new one. agent_id pins the call to a specific registered
        agent (without it, the orchestrator routes to the base assistant).
        """
        body: Dict[str, Any] = {}
        if query is not None:
            body["query"] = {"text": query}
        if session:
            if "/" not in session:  # bare ID or "-"
                session = f"{self.engine_path}/sessions/{session}"
            body["session"] = session
        if agent_id:
            body["agentsSpec"] = {"agentSpecs": [{"agentId": agent_id}]}
        if file_ids:
            body["fileIds"] = file_ids
        if tools_spec:
            body["toolsSpec"] = tools_spec
        if model_id:
            body["generationSpec"] = {"modelId": model_id}
        if force_assist:
            body["assistSkippingMode"] = "REQUEST_ASSIST"
        if user_metadata:
            body["userMetadata"] = user_metadata

        resp = requests.post(
            self._url(f"{self.assistant_path}:streamAssist"),
            headers=self._headers(),
            json=body,
            stream=True,
            timeout=timeout,
        )
        resp.raise_for_status()
        yield from _iter_json_array(resp)

    # -- convenience ---------------------------------------------------

    def ask(self, query: str, **kwargs: Any) -> "AssistResult":
        """One-shot helper: collect the whole stream into an AssistResult."""
        result = AssistResult()
        for chunk in self.stream_assist(query=query, **kwargs):
            result.add_chunk(chunk)
        return result

    def upload_file(
        self, path: str, session: str = "-", mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a local file into a session via :addContextFile.

        Returns the API response: {"session": ..., "fileId": ...}.
        session="-" creates a new session in the same call.
        """
        mime = mime_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            content = base64.b64encode(fh.read()).decode("ascii")
        r = requests.post(
            self._url(f"{self.engine_path}/sessions/{session}:addContextFile"),
            headers=self._headers(),
            json={
                "fileName": path.rsplit("/", 1)[-1],
                "mimeType": mime,
                "fileContents": content,
            },
            timeout=300,
        )
        r.raise_for_status()
        return r.json()

    def download_file(self, session_id: str, file_id: str, out_path: str) -> str:
        """Download a session context file (generated image/video/audio or upload)."""
        r = requests.get(
            self._url(f"{self.engine_path}/sessions/{session_id}:downloadFile"),
            headers=self._headers(),
            params={"fileId": file_id, "alt": "media"},
            allow_redirects=True,  # the API replies 302 to a signed URL
            timeout=300,
        )
        r.raise_for_status()
        with open(out_path, "wb") as fh:
            fh.write(r.content)
        return out_path

    def assist(self, query: str, session: Optional[str] = None) -> Dict[str, Any]:
        """Non-streaming :assist — one JSON object with the whole answer.

        Undocumented method (works on v1alpha today); prefer stream_assist
        for production use.
        """
        body: Dict[str, Any] = {"query": {"text": query}}
        if session:
            body["session"] = session
        r = requests.post(
            self._url(f"{self.assistant_path}:assist"),
            headers=self._headers(),
            json=body,
            timeout=300,
        )
        r.raise_for_status()
        return r.json()

    def a2a_message_stream(
        self, agent_id: str, text: str, context_id: Optional[str] = None,
        message_id: str = "msg-001", timeout: int = 600,
    ) -> Generator[Dict[str, Any], None, None]:
        """Native A2A surface: message the agent DIRECTLY (no orchestrator).

        Yields A2A stream items; the Gemini Enterprise answer structure is
        embedded under item["message"]["metadata"]. Note this surface is v1.
        """
        message: Dict[str, Any] = {
            "role": "ROLE_USER",
            "content": [{"text": text}],
            "messageId": message_id,
        }
        if context_id:
            message["contextId"] = context_id
        resp = requests.post(
            f"https://{self.host}/v1/{self.assistant_path}"
            f"/agents/{agent_id}/a2a/v1/message:stream",
            headers=self._headers(),
            json={"message": message},
            stream=True,
            timeout=timeout,
        )
        resp.raise_for_status()
        yield from _iter_json_array(resp)

    def list_agents(self) -> List[Dict[str, Any]]:
        r = requests.get(
            self._url(f"{self.assistant_path}/agents"),
            headers=self._headers(),
            params={"pageSize": 100},
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("agents", [])

    def list_sessions(self, page_size: int = 20) -> List[Dict[str, Any]]:
        r = requests.get(
            self._url(f"{self.engine_path}/sessions"),
            headers=self._headers(),
            params={"pageSize": page_size, "orderBy": "update_time desc"},
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("sessions", [])

    def delete_session(self, session_id: str) -> None:
        r = requests.delete(
            self._url(f"{self.engine_path}/sessions/{session_id}"),
            headers=self._headers(),
            timeout=60,
        )
        r.raise_for_status()


class AssistResult:
    """Accumulates stream chunks into text / thoughts / files / metadata."""

    def __init__(self) -> None:
        self.text: str = ""
        self.thoughts: str = ""
        self.files: List[Dict[str, str]] = []
        self.session: Optional[str] = None
        self.state: Optional[str] = None
        self.skipped_reasons: List[str] = []
        self.chunks: List[Dict[str, Any]] = []

    def add_chunk(self, chunk: Dict[str, Any]) -> None:
        self.chunks.append(chunk)
        if "error" in chunk:  # errors can arrive mid-stream with HTTP 200
            raise RuntimeError(f"streamAssist error chunk: {chunk['error']}")
        info = chunk.get("sessionInfo") or {}
        if info.get("session"):
            self.session = info["session"]
        answer = chunk.get("answer") or {}
        if answer.get("state"):
            self.state = answer["state"]
        self.skipped_reasons.extend(answer.get("assistSkippedReasons", []))
        for reply in answer.get("replies", []):
            content = (reply.get("groundedContent") or {}).get("content") or {}
            if content.get("thought"):
                self.thoughts += content.get("text", "")
            elif "text" in content:
                self.text += content["text"]
            if "file" in content:
                self.files.append(content["file"])

    @property
    def session_id(self) -> Optional[str]:
        return self.session.rsplit("/", 1)[-1] if self.session else None


def _iter_json_array(resp: requests.Response) -> Generator[Dict[str, Any], None, None]:
    """Incrementally decode a streamed JSON array of objects."""
    decoder = json.JSONDecoder()
    buf = ""
    for raw in resp.iter_content(chunk_size=None, decode_unicode=True):
        buf += raw
        while True:
            stripped = buf.lstrip()
            if not stripped or stripped[0] in "[,":
                buf = stripped[1:] if stripped else stripped
                if not stripped:
                    break
                continue
            if stripped[0] == "]":
                return
            try:
                obj, end = decoder.raw_decode(stripped)
            except json.JSONDecodeError:
                buf = stripped
                break  # need more bytes
            yield obj
            buf = stripped[end:]
