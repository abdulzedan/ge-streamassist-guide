"""Shared example bootstrap: builds a GEClient from the repo's .env file."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ge_streamassist import GEClient  # noqa: E402


def load_env() -> dict:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    values = {}
    if os.path.exists(env_path):
        with open(env_path) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):]
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip().strip('"')
    return values


def client() -> GEClient:
    env = load_env()
    try:
        return GEClient(
            project_id=os.environ.get("PROJECT_ID", env["PROJECT_ID"]),
            app_id=os.environ.get("APP_ID", env["APP_ID"]),
            location=os.environ.get("LOCATION", env.get("LOCATION", "global")),
        )
    except KeyError as missing:
        raise SystemExit(f"Set {missing} in .env (cp .env.example .env)") from None
