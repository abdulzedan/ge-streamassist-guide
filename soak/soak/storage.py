"""Result storage: GCS (JSON API over plain HTTPS) or a local directory.

No google-cloud-storage dependency on purpose - the harness stays on the
same two libraries as the guide's client (requests + google-auth).
"""

from __future__ import annotations

import json
import os
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Iterable

import requests

_GCS_API = "https://storage.googleapis.com/storage/v1"
_GCS_UPLOAD = "https://storage.googleapis.com/upload/storage/v1"


class Store:
    """Interface. Paths are '/'-separated keys relative to the store root."""

    def put_bytes(self, path: str, data: bytes, content_type: str) -> str:
        raise NotImplementedError

    def get_bytes(self, path: str) -> bytes | None:
        raise NotImplementedError

    def list(self, prefix: str) -> list[str]:
        raise NotImplementedError

    # convenience -----------------------------------------------------

    def put_json(self, path: str, obj: Any) -> str:
        data = json.dumps(obj, indent=1, sort_keys=False, default=str).encode()
        return self.put_bytes(path, data, "application/json")

    def put_text(self, path: str, text: str, content_type: str = "text/plain; charset=utf-8") -> str:
        return self.put_bytes(path, text.encode(), content_type)

    def get_json(self, path: str) -> Any | None:
        raw = self.get_bytes(path)
        return json.loads(raw) if raw else None

    def describe(self) -> str:
        raise NotImplementedError


class LocalStore(Store):
    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def put_bytes(self, path: str, data: bytes, content_type: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return str(target)

    def get_bytes(self, path: str) -> bytes | None:
        target = self.root / path
        return target.read_bytes() if target.exists() else None

    def list(self, prefix: str) -> list[str]:
        base = self.root / prefix
        if base.is_dir():
            files: Iterable[Path] = (p for p in base.rglob("*") if p.is_file())
        else:
            parent = base.parent
            if not parent.exists():
                return []
            files = (p for p in parent.rglob("*") if p.is_file() and str(p.relative_to(self.root)).startswith(prefix))
        return sorted(str(p.relative_to(self.root)) for p in files)

    def describe(self) -> str:
        return f"local:{self.root}"


class GcsStore(Store):
    def __init__(self, bucket: str, token_provider: Callable[[], str]) -> None:
        self.bucket = bucket
        self._token = token_provider
        self._http = requests.Session()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token()}"}

    def put_bytes(self, path: str, data: bytes, content_type: str) -> str:
        url = f"{_GCS_UPLOAD}/b/{self.bucket}/o"
        params = {"uploadType": "media", "name": path}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                r = self._http.post(
                    url, params=params, data=data, timeout=60,
                    headers={**self._headers(), "Content-Type": content_type},
                )
                if r.status_code < 300:
                    return f"gs://{self.bucket}/{path}"
                last_error = RuntimeError(f"GCS upload {r.status_code}: {r.text[:300]}")
                if r.status_code < 500 and r.status_code != 429:
                    break
            except requests.RequestException as exc:  # pragma: no cover - network
                last_error = exc
        raise RuntimeError(f"GCS upload failed for {path}: {last_error}")

    def get_bytes(self, path: str) -> bytes | None:
        url = f"{_GCS_API}/b/{self.bucket}/o/{urllib.parse.quote(path, safe='')}"
        r = self._http.get(url, params={"alt": "media"}, headers=self._headers(), timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.content

    def list(self, prefix: str) -> list[str]:
        names: list[str] = []
        token: str | None = None
        while True:
            params = {"prefix": prefix, "maxResults": 1000, "fields": "items(name),nextPageToken"}
            if token:
                params["pageToken"] = token
            r = self._http.get(f"{_GCS_API}/b/{self.bucket}/o", params=params, headers=self._headers(), timeout=60)
            r.raise_for_status()
            body = r.json()
            names.extend(item["name"] for item in body.get("items", []))
            token = body.get("nextPageToken")
            if not token:
                return sorted(names)

    def describe(self) -> str:
        return f"gs://{self.bucket}"


def make_store(bucket: str | None, local_dir: str | None, token_provider: Callable[[], str]) -> Store:
    if local_dir:
        return LocalStore(local_dir)
    if bucket:
        return GcsStore(bucket, token_provider)
    return LocalStore(os.environ.get("SOAK_OUTPUT_DIR", "soak/out"))
