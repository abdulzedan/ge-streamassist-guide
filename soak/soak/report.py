"""Aggregate run records into the report artifact: report.md, report.json,
calls.csv, runs.csv, checks.csv."""

from __future__ import annotations

import csv
import io
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import __version__
from .checks import FAST_CHECKS, HEAVY_CHECKS
from .config import Config
from .http import Auth
from .runner import SLOT_SECONDS, log, parse_iso
from .storage import Store, make_store

PT = ZoneInfo("America/Los_Angeles")   # feature quotas reset at midnight Pacific
_SPEC_BY_NAME = {s.name: s for s in FAST_CHECKS + HEAVY_CHECKS}


# -- small helpers ---------------------------------------------------------

def pct(values: list[float], p: float) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = max(0, min(len(vals) - 1, math.ceil(p / 100 * len(vals)) - 1))
    return vals[k]


def ms(v: float | None) -> str:
    if v is None:
        return "-"
    return f"{v / 1000:.1f} s" if v >= 1000 else f"{int(v)} ms"


def rate(n: int, d: int) -> str:
    return "-" if not d else f"{100 * n / d:.1f}%"


def iso(dt: datetime | None) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ") if dt else "-"


def norm_message(msg: str) -> str:
    msg = re.sub(r"\d+", "#", msg or "")
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg[:140]


# -- loading -----------------------------------------------------------------

def load_runs(store: Store, start: datetime, end: datetime) -> list[dict]:
    day = start.date()
    names: list[str] = []
    while day <= end.date():
        names.extend(store.list(f"runs/{day:%Y-%m-%d}/"))
        day += timedelta(days=1)
    runs: list[dict] = []
    for name in names:
        rec = store.get_json(name)
        if not rec or "started_at" not in rec:
            continue
        started = parse_iso(rec["started_at"])
        if started and start <= started < end:
            rec["_path"] = name
            runs.append(rec)
    runs.sort(key=lambda r: r["started_at"])
    return runs


# -- model -------------------------------------------------------------------

def build_model(runs: list[dict], cfg: Config, campaign: dict, start: datetime, end: datetime) -> dict:
    now = datetime.now(timezone.utc)
    fast = [r for r in runs if r["tier"] == "fast"]
    heavy = [r for r in runs if r["tier"] == "heavy"]
    calls = [dict(c, _run=r) for r in runs for c in r.get("calls", [])]
    checks = [dict(c, _run=r) for r in runs for c in r.get("checks", [])]

    # scheduler reliability: which 5-minute slots should have produced a fast run
    first_slot = math.ceil(start.timestamp() / SLOT_SECONDS)
    last_slot = math.floor((min(end, now).timestamp() - 240) / SLOT_SECONDS)   # give the current slot time to finish
    expected_slots = set(range(first_slot, last_slot + 1)) if last_slot >= first_slot else set()
    seen_slots = Counter(r["slot"] for r in fast)
    missed = sorted(expected_slots - set(seen_slots))
    duplicates = sorted(s for s, n in seen_slots.items() if n > 1)
    late = [r["late_ms"] for r in fast]
    durations = [r["duration_ms"] for r in fast]

    # usage
    by_verb: dict[str, dict] = {}
    for c in calls:
        v = by_verb.setdefault(c["verb"], {"count": 0, "ok": 0, "latencies": [], "ttfb": []})
        v["count"] += 1
        v["ok"] += 1 if c["ok"] else 0
        if c.get("latency_ms") is not None:
            v["latencies"].append(c["latency_ms"])
        if c.get("ttfb_ms") is not None:
            v["ttfb"].append(c["ttfb_ms"])
    verbs = {
        k: {"count": v["count"], "ok": v["ok"], "fail": v["count"] - v["ok"],
            "p50_ms": pct(v["latencies"], 50), "p95_ms": pct(v["latencies"], 95), "max_ms": pct(v["latencies"], 100),
            "ttfb_p50_ms": pct(v["ttfb"], 50)}
        for k, v in sorted(by_verb.items(), key=lambda kv: -kv[1]["count"])
    }
    assist_calls = [c for c in calls if c.get("assist_query")]
    assist_ok = [c for c in assist_calls if c["ok"]]
    quota_errors = [c for c in calls if (c.get("error") or {}).get("is_quota")]
    per_pt_day = Counter(parse_iso(c["started_at"]).astimezone(PT).strftime("%Y-%m-%d") for c in assist_calls)
    pool = cfg.license_count * cfg.license_limit

    # hourly timeline
    hourly: dict[str, dict] = {}
    cursor = start.replace(minute=0, second=0, microsecond=0)
    while cursor < min(end, now) + timedelta(hours=1):
        hourly[cursor.strftime("%Y-%m-%d %H:00Z")] = {"runs": 0, "calls": 0, "assist_queries": 0, "failed_calls": 0,
                                                       "failed_checks": 0, "latencies": [], "hour": cursor}
        cursor += timedelta(hours=1)
    for r in runs:
        key = parse_iso(r["started_at"]).strftime("%Y-%m-%d %H:00Z")
        h = hourly.setdefault(key, {"runs": 0, "calls": 0, "assist_queries": 0, "failed_calls": 0, "failed_checks": 0,
                                    "latencies": [], "hour": parse_iso(r["started_at"]).replace(minute=0, second=0, microsecond=0)})
        h["runs"] += 1
        h["failed_checks"] += len(r["summary"].get("checks_failed", []))
    for c in calls:
        key = parse_iso(c["started_at"]).strftime("%Y-%m-%d %H:00Z")
        h = hourly.setdefault(key, {"runs": 0, "calls": 0, "assist_queries": 0, "failed_calls": 0, "failed_checks": 0,
                                    "latencies": [], "hour": parse_iso(c["started_at"]).replace(minute=0, second=0, microsecond=0)})
        h["calls"] += 1
        h["assist_queries"] += 1 if c.get("assist_query") else 0
        h["failed_calls"] += 0 if c["ok"] else 1
        if c.get("assist_query") and c.get("latency_ms") is not None:
            h["latencies"].append(c["latency_ms"])
    timeline = []
    cum_by_pt_day: Counter = Counter()
    for key in sorted(hourly):
        h = hourly[key]
        pt_day = h["hour"].astimezone(PT).strftime("%Y-%m-%d")
        cum_by_pt_day[pt_day] += h["assist_queries"]
        timeline.append({"hour_utc": key, "runs": h["runs"], "calls": h["calls"], "assist_queries": h["assist_queries"],
                         "failed_calls": h["failed_calls"], "failed_checks": h["failed_checks"],
                         "assist_p95_ms": pct(h["latencies"], 95), "pt_day": pt_day,
                         "cumulative_assist_queries_pt_day": cum_by_pt_day[pt_day]})
    while timeline and timeline[-1]["runs"] == 0 and timeline[-1]["calls"] == 0:
        timeline.pop()

    # per-check results
    per_check: dict[str, dict] = {}
    for c in checks:
        entry = per_check.setdefault(c["name"], {"attempts": 0, "pass": 0, "durations": [], "failed_assertions": Counter(),
                                                 "observations": defaultdict(lambda: [0, 0]), "errors": 0, "tier": c["tier"]})
        entry["attempts"] += 1
        entry["pass"] += 1 if c["ok"] else 0
        entry["durations"].append(c["duration_ms"])
        entry["errors"] += 1 if c.get("error") else 0
        for name in c.get("failed", []):
            entry["failed_assertions"][name] += 1
        for name, ok in (c.get("observations") or {}).items():
            entry["observations"][name][1] += 1
            entry["observations"][name][0] += 1 if ok else 0
    check_table = []
    order = [s.name for s in FAST_CHECKS + HEAVY_CHECKS]
    for name in sorted(per_check, key=lambda n: order.index(n) if n in order else 99):
        e = per_check[name]
        spec = _SPEC_BY_NAME.get(name)
        check_table.append({
            "check": name, "tier": e["tier"], "description": spec.description if spec else "",
            "attempts": e["attempts"], "pass": e["pass"], "fail": e["attempts"] - e["pass"],
            "pass_rate": rate(e["pass"], e["attempts"]),
            "p50_ms": pct(e["durations"], 50), "p95_ms": pct(e["durations"], 95), "max_ms": pct(e["durations"], 100),
            "failed_assertions": dict(e["failed_assertions"].most_common(5)),
            "observations": {k: {"true": v[0], "total": v[1], "rate": rate(v[0], v[1])} for k, v in e["observations"].items()},
        })

    # error catalog
    catalog: dict[tuple, dict] = {}
    for c in calls:
        err = c.get("error")
        if not err:
            continue
        key = (err.get("kind"), err.get("code"), err.get("status"), norm_message(err.get("message", "")))
        e = catalog.setdefault(key, {"kind": key[0], "code": key[1], "status": key[2], "message": key[3], "count": 0,
                                     "first_seen": c["started_at"], "last_seen": c["started_at"], "verbs": Counter(),
                                     "checks": Counter(), "sample": {"run_id": c["_run"]["run_id"], "assist_token": c.get("assist_token"),
                                                                     "check": c["check"], "verb": c["verb"], "call_id": c["call_id"]}})
        e["count"] += 1
        e["last_seen"] = max(e["last_seen"], c["started_at"])
        e["first_seen"] = min(e["first_seen"], c["started_at"])
        e["verbs"][c["verb"]] += 1
        e["checks"][c["check"]] += 1
    errors = sorted(({**e, "verbs": dict(e["verbs"]), "checks": dict(e["checks"])} for e in catalog.values()),
                    key=lambda e: -e["count"])

    # probe availability + longest outage
    probe_calls = sorted((c for c in calls if c["check"] == "probe" and c["verb"] == "streamAssist"), key=lambda c: c["started_at"])
    longest = {"count": 0, "from": None, "to": None}
    streak: list[dict] = []
    for c in probe_calls + [None]:
        if c is not None and not c["ok"]:
            streak.append(c)
            continue
        if len(streak) > longest["count"]:
            longest = {"count": len(streak), "from": streak[0]["started_at"], "to": streak[-1]["started_at"]}
        streak = []

    return {
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "harness_version": __version__,
        "window": {"start": start.isoformat().replace("+00:00", "Z"), "end": end.isoformat().replace("+00:00", "Z"),
                   "hours": round((min(end, now) - start).total_seconds() / 3600, 2),
                   "complete": now >= end},
        "campaign": campaign,
        "target": {"project_id": cfg.project_id, "location": cfg.location, "app_id": cfg.app_id,
                   "assistant_id": cfg.assistant_id, "api_version": cfg.api_version},
        "identities": sorted({r.get("identity", "?") for r in runs}),
        "images": sorted({(r.get("env") or {}).get("git_sha", "?") for r in runs}),
        "profiles": sorted({r.get("profile", "?") for r in runs}),
        "scheduler": {
            "fast_expected": len(expected_slots), "fast_seen": len(fast), "fast_missed": len(missed),
            "fast_missed_slots": [datetime.fromtimestamp(s * SLOT_SECONDS, tz=timezone.utc).strftime("%Y-%m-%d %H:%MZ") for s in missed][:50],
            "fast_duplicate_slots": len(duplicates), "heavy_seen": len(heavy),
            "late_p50_ms": pct(late, 50), "late_p95_ms": pct(late, 95), "late_max_ms": pct(late, 100),
            "duration_p50_ms": pct(durations, 50), "duration_p95_ms": pct(durations, 95), "duration_max_ms": pct(durations, 100),
        },
        "usage": {
            "calls_total": len(calls), "calls_ok": sum(1 for c in calls if c["ok"]),
            "assist_queries": len(assist_calls), "assist_queries_ok": len(assist_ok),
            "assist_success_rate": rate(len(assist_ok), len(assist_calls)),
            "assist_p50_ms": pct([c["latency_ms"] for c in assist_calls if c.get("latency_ms") is not None], 50),
            "assist_p95_ms": pct([c["latency_ms"] for c in assist_calls if c.get("latency_ms") is not None], 95),
            "assist_max_ms": pct([c["latency_ms"] for c in assist_calls if c.get("latency_ms") is not None], 100),
            "assist_ttfb_p50_ms": pct([c["ttfb_ms"] for c in assist_calls if c.get("ttfb_ms") is not None], 50),
            "per_license_limit": cfg.license_limit, "license_edition": cfg.license_edition,
            "license_count": cfg.license_count, "pool_limit": pool,
            "assist_vs_one_license": round(len(assist_calls) / cfg.license_limit, 2) if cfg.license_limit else None,
            "assist_vs_pool": rate(len(assist_calls), pool),
            "assist_queries_per_pt_day": dict(sorted(per_pt_day.items())),
            "quota_errors": len(quota_errors),
            "first_quota_error": ({"at": quota_errors[0]["started_at"], "verb": quota_errors[0]["verb"],
                                   "error": quota_errors[0]["error"],
                                   "assist_queries_before": sum(1 for c in assist_calls if c["started_at"] < quota_errors[0]["started_at"])}
                                  if quota_errors else None),
            "by_verb": verbs,
        },
        "availability": {
            "probe_attempts": len(probe_calls), "probe_ok": sum(1 for c in probe_calls if c["ok"]),
            "probe_success_rate": rate(sum(1 for c in probe_calls if c["ok"]), len(probe_calls)),
            "longest_probe_failure_streak": longest,
        },
        "timeline": timeline,
        "checks": check_table,
        "errors": errors[:40],
        "run_count": len(runs),
    }


# -- rendering ---------------------------------------------------------------

def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def render_md(m: dict) -> str:
    u, s, a = m["usage"], m["scheduler"], m["availability"]
    w = m["window"]
    lines = [
        "# Gemini Enterprise Stream Assist - 24h soak report",
        "",
        f"Generated {m['generated_at']} by ge-soak {m['harness_version']}. "
        f"Window {w['start']} to {w['end']} ({w['hours']} h{'' if w['complete'] else ', still running'}).",
        "",
        f"Target: `{m['target']['app_id']}` in `{m['target']['project_id']}` ({m['target']['location']}, {m['target']['api_version']}). "
        f"Caller identity: {', '.join(m['identities']) or '-'}. Image: {', '.join(m['images']) or '-'}. Profile: {', '.join(m['profiles']) or '-'}.",
        "",
        "## Headline",
        "",
        _table(["Metric", "Value"], [
            ["Runs recorded", f"{m['run_count']} ({s['fast_seen']} fast, {s['heavy_seen']} heavy)"],
            ["Fast slots expected / seen / missed", f"{s['fast_expected']} / {s['fast_seen']} / {s['fast_missed']}"],
            ["API calls (all verbs)", f"{u['calls_total']} ({u['calls_ok']} ok)"],
            ["Assistant queries (streamAssist + assist + native A2A)", f"{u['assist_queries']} ({u['assist_queries_ok']} ok, {u['assist_success_rate']})"],
            [f"vs one {u['license_edition']} license ({u['per_license_limit']}/day)", f"{u['assist_vs_one_license']}x"],
            [f"vs the pooled quota ({u['license_count']} licenses x {u['per_license_limit']} = {u['pool_limit']}/day)", u["assist_vs_pool"]],
            ["Quota errors (429 / RESOURCE_EXHAUSTED)", u["quota_errors"] if not u["first_quota_error"] else
             f"{u['quota_errors']}, first at {u['first_quota_error']['at']} after {u['first_quota_error']['assist_queries_before']} queries"],
            ["Probe availability", f"{a['probe_success_rate']} ({a['probe_ok']}/{a['probe_attempts']})"],
            ["Longest probe failure streak", (f"{a['longest_probe_failure_streak']['count']} runs, {a['longest_probe_failure_streak']['from']} to {a['longest_probe_failure_streak']['to']}"
                                              if a["longest_probe_failure_streak"]["count"] else "none")],
            ["Assistant query latency p50 / p95 / max", f"{ms(u['assist_p50_ms'])} / {ms(u['assist_p95_ms'])} / {ms(u['assist_max_ms'])}"],
            ["Time to first byte p50 (assist calls)", ms(u["assist_ttfb_p50_ms"])],
        ]),
        "",
        "Assistant queries per Pacific calendar day (the quota window resets at midnight PT):",
        "",
        _table(["PT day", "Assistant queries", f"% of one license ({u['per_license_limit']})", f"% of pool ({u['pool_limit']})"],
               [[d, n, rate(n, u["per_license_limit"]), rate(n, u["pool_limit"])] for d, n in u["assist_queries_per_pt_day"].items()]) or "(none)",
        "",
        "## Scheduler and runtime",
        "",
        _table(["Metric", "p50", "p95", "max"], [
            ["Start delay after the 5-minute mark", ms(s["late_p50_ms"]), ms(s["late_p95_ms"]), ms(s["late_max_ms"])],
            ["Fast run duration", ms(s["duration_p50_ms"]), ms(s["duration_p95_ms"]), ms(s["duration_max_ms"])],
        ]),
        "",
        (f"Missed fast slots: {', '.join(s['fast_missed_slots'])}" if s["fast_missed_slots"] else "No missed fast slots.")
        + (f" Duplicate slots: {s['fast_duplicate_slots']}." if s["fast_duplicate_slots"] else ""),
        "",
        "## Capability results",
        "",
        _table(["Check", "Tier", "Attempts", "Pass", "Fail", "Pass rate", "p50", "p95", "max", "Failed assertions", "Observations"], [
            [c["check"], c["tier"], c["attempts"], c["pass"], c["fail"], c["pass_rate"], ms(c["p50_ms"]), ms(c["p95_ms"]), ms(c["max_ms"]),
             ", ".join(f"{k} x{v}" for k, v in c["failed_assertions"].items()) or "-",
             ", ".join(f"{k} {v['rate']}" for k, v in c["observations"].items()) or "-"]
            for c in m["checks"]]) if m["checks"] else "(no checks recorded)",
        "",
        "What each check does:",
        "",
        "\n".join(f"- `{c['check']}`: {c['description']}" for c in m["checks"]),
        "",
        "## Per-verb latency",
        "",
        _table(["Verb", "Calls", "OK", "Fail", "p50", "p95", "max", "TTFB p50"], [
            [v, d["count"], d["ok"], d["fail"], ms(d["p50_ms"]), ms(d["p95_ms"]), ms(d["max_ms"]), ms(d["ttfb_p50_ms"])]
            for v, d in u["by_verb"].items()]) if u["by_verb"] else "(no calls)",
        "",
        "## Hourly timeline (UTC)",
        "",
        _table(["Hour", "Runs", "Calls", "Assist queries", "Failed calls", "Failed checks", "Assist p95", "Cumulative (PT day)"], [
            [t["hour_utc"], t["runs"], t["calls"], t["assist_queries"], t["failed_calls"], t["failed_checks"], ms(t["assist_p95_ms"]),
             f"{t['cumulative_assist_queries_pt_day']} ({t['pt_day']})"] for t in m["timeline"]]) if m["timeline"] else "(empty)",
        "",
        "## Errors",
        "",
        (_table(["Kind", "Code", "Status", "Message (digits masked)", "Count", "First", "Last", "Verbs", "Sample run / assistToken"], [
            [e["kind"], e["code"] or "-", e["status"] or "-", e["message"], e["count"], e["first_seen"], e["last_seen"],
             ", ".join(f"{k} x{v}" for k, v in e["verbs"].items()),
             f"{e['sample']['run_id']} / {e['sample']['assist_token'] or '-'}"] for e in m["errors"]])
         if m["errors"] else "No call-level errors in the window."),
        "",
        "## Artifacts",
        "",
        "- `report.json`: this report as data",
        "- `calls.csv`: one row per API call (timestamp, verb, status, latency, assistToken, error)",
        "- `runs.csv`: one row per scheduled run",
        "- `checks.csv`: one row per check execution with failed assertions and observations",
        "- `runs/YYYY-MM-DD/*.json` in the bucket: full evidence per run (request excerpts, response excerpts, planner traces)",
        "",
    ]
    return "\n".join(lines)


def to_csvs(runs: list[dict]) -> dict[str, str]:
    calls_buf, runs_buf, checks_buf = io.StringIO(), io.StringIO(), io.StringIO()
    cw = csv.writer(calls_buf)
    cw.writerow(["started_at", "run_id", "tier", "check", "verb", "api_version", "assist_query", "status", "ok",
                 "latency_ms", "ttfb_ms", "first_chunk_ms", "bytes", "chunks", "answer_state", "error_kind", "error_code",
                 "error_status", "is_quota", "assist_token", "session", "text_chars", "planner_calls", "grounding_refs"])
    rw = csv.writer(runs_buf)
    rw.writerow(["run_id", "tier", "profile", "slot", "scheduled_at", "started_at", "finished_at", "late_ms", "duration_ms",
                 "identity", "git_sha", "checks_total", "checks_ok", "checks_failed", "calls_total", "calls_ok",
                 "assist_queries", "quota_errors"])
    kw = csv.writer(checks_buf)
    kw.writerow(["run_id", "tier", "started_at", "check", "ok", "duration_ms", "failed", "observations", "notes"])
    for r in runs:
        s = r["summary"]
        rw.writerow([r["run_id"], r["tier"], r.get("profile"), r["slot"], r["scheduled_at"], r["started_at"], r["finished_at"],
                     r["late_ms"], r["duration_ms"], r.get("identity"), (r.get("env") or {}).get("git_sha"),
                     s["checks_total"], s["checks_ok"], ";".join(s["checks_failed"]), s["calls_total"], s["calls_ok"],
                     s["assist_queries"], s["quota_errors"]])
        for c in r.get("checks", []):
            kw.writerow([r["run_id"], c["tier"], c["started_at"], c["name"], c["ok"], c["duration_ms"],
                         ";".join(c.get("failed", [])), json.dumps(c.get("observations") or {}), json.dumps(c.get("notes") or {})])
        for c in r.get("calls", []):
            e = c.get("error") or {}
            cw.writerow([c["started_at"], r["run_id"], r["tier"], c["check"], c["verb"], c["api_version"], c["assist_query"],
                         c["status"], c["ok"], c["latency_ms"], c["ttfb_ms"], c["first_chunk_ms"], c["bytes"], c["chunks"],
                         c["answer_state"], e.get("kind"), e.get("code"), e.get("status"), e.get("is_quota"),
                         c["assist_token"], c["session"], c["text_chars"], ";".join(c.get("planner_calls", [])), c["grounding_refs"]])
    return {"calls.csv": calls_buf.getvalue(), "runs.csv": runs_buf.getvalue(), "checks.csv": checks_buf.getvalue()}


# -- entry point ---------------------------------------------------------------

def resolve_window(campaign: dict, start: str | None, end: str | None, window_hours: float | None) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if start and end:
        return parse_iso(start), parse_iso(end)
    if window_hours:
        e = parse_iso(end) if end else now
        return e - timedelta(hours=window_hours), e
    if campaign.get("start_at"):
        s = parse_iso(campaign["start_at"])
        e = parse_iso(end) if end else (parse_iso(campaign.get("end_at")) or now)
        return s, e
    e = parse_iso(end) if end else now
    return e - timedelta(hours=24), e


def build_and_publish(local_dir: str | None, label: str, start: str | None, end: str | None,
                      window_hours: float | None, upload: bool, out_dir: str | None) -> int:
    cfg = Config.from_env()
    auth = Auth()
    store = make_store(cfg.bucket, local_dir, auth.token)
    campaign = store.get_json("campaign.json") or {}
    w_start, w_end = resolve_window(campaign, start, end, window_hours)
    runs = load_runs(store, w_start, w_end)
    model = build_model(runs, cfg, campaign, w_start, w_end)
    md = render_md(model)
    files = {"report.md": (md, "text/markdown; charset=utf-8"),
             "report.json": (json.dumps(model, indent=1, default=str), "application/json"),
             **{k: (v, "text/csv") for k, v in to_csvs(runs).items()}}
    print(md)
    written = []
    if upload:
        for name, (content, ctype) in files.items():
            written.append(store.put_text(f"reports/{label}/{name}", content, ctype))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for name, (content, _) in files.items():
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
                fh.write(content)
            written.append(os.path.join(out_dir, name))
    log("INFO", "report published", label=label, runs=len(runs), window=model["window"], written=written)
    return 0
