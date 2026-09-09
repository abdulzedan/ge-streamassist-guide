"""One scheduled execution: decide which checks are due, run them, persist
the run record."""

from __future__ import annotations

import json
import platform
import time
import uuid
from datetime import datetime, timezone

from . import __version__
from .checks import FAST_CHECKS, HEAVY_CHECKS, Ctx, due, run_check
from .config import Config
from .http import Api, Auth
from .storage import Store, make_store

SLOT_SECONDS = 300            # the fast cadence
HEAVY_SLOTS = 48              # heavy cadence = every 4h = 48 fast slots


def log(severity: str, message: str, **fields) -> None:
    """Structured stdout line: Cloud Logging parses severity/message."""
    print(json.dumps({"severity": severity, "message": message, **fields}, default=str), flush=True)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def campaign_state(store: Store, now: datetime) -> tuple[dict, str]:
    """Returns (campaign, status) where status is active | before | ended | none."""
    campaign = store.get_json("campaign.json") or {}
    if not campaign:
        return campaign, "none"
    start, end = parse_iso(campaign.get("start_at")), parse_iso(campaign.get("end_at"))
    if start and now < start:
        return campaign, "before"
    if end and now >= end:
        return campaign, "ended"
    return campaign, "active"


def run(tier: str, local_dir: str | None = None, profile_override: str | None = None,
        force_all: bool = False, ignore_campaign: bool = False, only: set[str] | None = None) -> int:
    cfg = Config.from_env()
    auth = Auth()
    store = make_store(cfg.bucket, local_dir, auth.token)
    now = datetime.now(timezone.utc)
    slot = int(now.timestamp()) // SLOT_SECONDS
    scheduled_at = datetime.fromtimestamp(slot * SLOT_SECONDS, tz=timezone.utc)
    heavy_index = slot // HEAVY_SLOTS

    campaign, status = campaign_state(store, now)
    profile = profile_override or campaign.get("profile") or "standard"
    if status in ("before", "ended") and not ignore_campaign:
        log("INFO", f"campaign {status}; no calls made", tier=tier, campaign=campaign.get("id"), status=status)
        return 0

    run_id = f"{now:%Y%m%dT%H%M%SZ}-{tier}-{uuid.uuid4().hex[:6]}"
    api = Api(cfg, auth)
    ctx = Ctx(cfg=cfg, api=api, run_id=run_id, tier=tier, slot=slot, heavy_index=heavy_index,
              project_number=cfg.project_number)
    specs = FAST_CHECKS if tier == "fast" else HEAVY_CHECKS
    index = slot if tier == "fast" else heavy_index
    chosen = [s for s in specs if ((s.name in only) if only else (force_all or due(s, index, profile)))]
    log("INFO", f"run {run_id} start", tier=tier, slot=slot, profile=profile,
        checks=[s.name for s in chosen], identity=auth.identity(), store=store.describe())

    t0 = time.perf_counter()
    results = [run_check(spec, ctx) for spec in chosen]
    duration_ms = int((time.perf_counter() - t0) * 1000)

    calls = [c.to_dict() for c in api.calls]
    quota_errors = [c for c in api.calls if c.error and c.error.is_quota]
    summary = {
        "checks_total": len(results),
        "checks_ok": sum(1 for r in results if r.ok),
        "checks_failed": [r.name for r in results if not r.ok],
        "calls_total": len(api.calls),
        "calls_ok": sum(1 for c in api.calls if c.ok),
        "assist_queries": sum(1 for c in api.calls if c.assist_query),
        "assist_queries_ok": sum(1 for c in api.calls if c.assist_query and c.ok),
        "quota_errors": len(quota_errors),
        "duration_ms": duration_ms,
    }
    finished = datetime.now(timezone.utc)
    record = {
        "schema": 1,
        "harness_version": __version__,
        "run_id": run_id,
        "tier": tier,
        "profile": profile,
        "campaign_id": campaign.get("id"),
        "slot": slot,
        "heavy_index": heavy_index,
        "scheduled_at": scheduled_at.isoformat().replace("+00:00", "Z"),
        "started_at": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "finished_at": finished.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "late_ms": int((now - scheduled_at).total_seconds() * 1000),
        "duration_ms": duration_ms,
        "identity": auth.identity(),
        "config": cfg.summary(),
        "env": {"python": platform.python_version(), "git_sha": cfg.git_sha, "region": cfg.region},
        "summary": summary,
        "checks": [r.to_dict() for r in results],
        "calls": calls,
    }
    path = f"runs/{now:%Y-%m-%d}/{now:%H%M%S}_{tier}_{slot}.json"
    try:
        where = store.put_json(path, record)
    except Exception as exc:  # keep the evidence in the logs at least
        log("ERROR", f"could not persist run record: {exc}", run_id=run_id, record=record)
        return 1
    log("INFO" if not summary["checks_failed"] else "WARNING", f"run {run_id} done", run_id=run_id,
        tier=tier, slot=slot, stored=where, **summary)
    for r in results:
        if not r.ok:
            log("WARNING", f"check {r.name} failed", run_id=run_id,
                failed=[a.to_dict() for a in r.assertions if a.critical and not a.ok], error=r.error)
    return 0
