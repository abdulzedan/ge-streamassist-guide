#!/usr/bin/env python3
"""Check relative Markdown links without requiring network access."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^]]*]\(([^)]+)\)")


def main() -> int:
    missing: list[str] = []
    for document in sorted(ROOT.rglob("*.md")):
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            target = target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path = unquote(target.split("#", 1)[0])
            if path and not (document.parent / path).resolve().exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    if missing:
        print("missing relative Markdown links:")
        print("\n".join(f"  {item}" for item in missing))
        return 1
    print("relative Markdown links: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
