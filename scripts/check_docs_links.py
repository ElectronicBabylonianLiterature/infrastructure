#!/usr/bin/env python3
"""Check local file links in Markdown without fetching external pages.

This is a documentation-only validation tool. It does not inspect live hosts,
Docker services, secrets or certificate storage.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
SCHEMES = {"http", "https", "mailto", "tel", "data"}


def destination(text: str) -> str:
    value = text.strip()
    if value.startswith("<"):
        return value[1:].split(">", 1)[0]
    # Markdown optional link titles are separate from the unquoted URL.
    return value.split()[0] if value else ""


def check() -> int:
    errors: list[str] = []
    docs = sorted(ROOT.rglob("*.md"))
    links = 0
    for file in docs:
        # Git metadata must never be treated as a documentation source.
        if ".git" in file.relative_to(ROOT).parts:
            continue
        text = file.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            target = destination(match.group(1))
            if not target or target.startswith("#"):
                continue
            parts = urlsplit(target)
            if parts.scheme.lower() in SCHEMES or parts.netloc:
                continue
            if parts.scheme:
                continue
            local = unquote(parts.path)
            if not local:
                continue
            links += 1
            path = (file.parent / local).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{file.relative_to(ROOT)}:{line}: "
                    f"missing local link: {target}"
                )

    for error in errors:
        print(error, file=sys.stderr)
    print(f"Checked {links} local file links across {len(docs)} Markdown documents.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(check())
