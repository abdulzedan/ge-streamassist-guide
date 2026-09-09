"""Environment-driven configuration for the soak harness."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _require(name: str) -> str:
    value = _env(name)
    if value is None:
        raise SystemExit(f"config: environment variable {name} is required")
    return value


@dataclass(frozen=True)
class Config:
    # --- target app (same names as the repo's .env) ---
    project_id: str
    location: str
    app_id: str
    assistant_id: str
    api_version: str
    project_number: str | None
    # --- where results go ---
    bucket: str | None
    # --- fixtures used by the capability checks ---
    adk_agent_id: str
    a2a_agent_id: str
    data_store_id: str
    model_id: str
    # --- quota context for the report ---
    license_limit: int      # per-license Assistant queries/day (Standard = 160)
    license_count: int      # licenses in the pool for this project+location
    license_edition: str
    # --- provenance ---
    git_sha: str
    region: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            project_id=_require("PROJECT_ID"),
            location=_env("LOCATION", "global"),
            app_id=_require("APP_ID"),
            assistant_id=_env("ASSISTANT_ID", "default_assistant"),
            api_version=_env("API_VERSION", "v1alpha"),
            project_number=_env("SOAK_PROJECT_NUMBER"),
            bucket=_env("SOAK_BUCKET"),
            adk_agent_id=_env("SOAK_ADK_AGENT_ID", "11867618434103444869"),
            a2a_agent_id=_env("SOAK_A2A_AGENT_ID", "1030712722314703187"),
            data_store_id=_env("SOAK_DATA_STORE_ID", "architecture-documentation_1770737462806"),
            model_id=_env("SOAK_MODEL_ID", "gemini-2.5-flash"),
            license_limit=int(_env("SOAK_LICENSE_LIMIT", "160")),
            license_count=int(_env("SOAK_LICENSE_COUNT", "20")),
            license_edition=_env("SOAK_LICENSE_EDITION", "Standard"),
            git_sha=_env("GIT_SHA", "dev"),
            region=_env("SOAK_REGION", "us-central1"),
        )

    # --- derived API addressing (mirrors snippets/curl/common.sh) ---

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

    def url(self, path_and_verb: str, version: str | None = None) -> str:
        return f"https://{self.host}/{version or self.api_version}/{path_and_verb}"

    def data_store_path(self, data_store_id: str) -> str:
        # The API reference wants the project NUMBER here (gotcha 24).
        proj = self.project_number or self.project_id
        return (
            f"projects/{proj}/locations/{self.location}"
            f"/collections/default_collection/dataStores/{data_store_id}"
        )

    def summary(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_number": self.project_number,
            "location": self.location,
            "app_id": self.app_id,
            "assistant_id": self.assistant_id,
            "api_version": self.api_version,
            "bucket": self.bucket,
            "adk_agent_id": self.adk_agent_id,
            "a2a_agent_id": self.a2a_agent_id,
            "data_store_id": self.data_store_id,
            "model_id": self.model_id,
            "license_limit": self.license_limit,
            "license_count": self.license_count,
            "license_edition": self.license_edition,
            "git_sha": self.git_sha,
            "region": self.region,
        }
