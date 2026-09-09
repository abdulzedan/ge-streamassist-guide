"""CLI: python -m soak run --tier fast|heavy | python -m soak report [...]"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="soak", description="Gemini Enterprise Stream Assist soak test")
    parser.add_argument("--local", metavar="DIR", help="write/read results in a local directory instead of GCS")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="execute one scheduled run")
    p_run.add_argument("--tier", choices=("fast", "heavy"), default="fast")
    p_run.add_argument("--profile", choices=("standard", "full", "probe"), help="override campaign profile")
    p_run.add_argument("--all", action="store_true", help="run every check of the tier regardless of cadence")
    p_run.add_argument("--only", help="comma-separated check names to run (ignores cadence)")
    p_run.add_argument("--ignore-campaign", action="store_true", help="run even if no campaign is active")

    p_rep = sub.add_parser("report", help="aggregate run records into the report artifact")
    p_rep.add_argument("--label", default="latest", help="reports/<label>/ output folder")
    p_rep.add_argument("--start", help="window start (ISO 8601, UTC)")
    p_rep.add_argument("--end", help="window end (ISO 8601, UTC)")
    p_rep.add_argument("--window-hours", type=float, help="rolling window ending now (or at --end)")
    p_rep.add_argument("--no-upload", action="store_true", help="print only; do not write reports/")
    p_rep.add_argument("--out", metavar="DIR", help="also write the artifact files to this local directory")

    args = parser.parse_args(argv)
    if args.command == "run":
        from .runner import run
        return run(args.tier, local_dir=args.local, profile_override=args.profile,
                   force_all=args.all, ignore_campaign=args.ignore_campaign,
                   only=set(args.only.split(",")) if args.only else None)
    if args.command == "report":
        from .report import build_and_publish
        return build_and_publish(local_dir=args.local, label=args.label, start=args.start, end=args.end,
                                 window_hours=args.window_hours, upload=not args.no_upload, out_dir=args.out)
    return 2


if __name__ == "__main__":
    sys.exit(main())
