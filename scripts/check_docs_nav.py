#!/usr/bin/env python3
"""Fail if any Diátaxis docs page is missing from the VitePress sidebar.

The sidebar in ``.vitepress/config.mts`` is hand-maintained, so a newly added
tutorial / how-to / explanation / reference page is easy to forget — it then
ships but is unreachable from the nav (this happened with several pages before
this check existed). Run in CI so an orphan page fails the build.

Only the Diátaxis directories are checked; FT reports, ADRs, roadmap, todo,
review dailies, and templates are intentionally not in the sidebar.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CONFIG = ROOT / ".vitepress" / "config.mts"
DIATAXIS_DIRS = ("tutorials", "how-to", "howto", "explanation", "reference")


def _site_link(md: Path) -> str:
    """Map a docs file to its cleanUrls site path, e.g. /how-to/run-tests."""
    return "/" + str(md.relative_to(DOCS).with_suffix(""))


def _diataxis_pages() -> list[Path]:
    pages: list[Path] = []
    for base in (DOCS, DOCS / "ja"):
        for directory in DIATAXIS_DIRS:
            for md in sorted((base / directory).glob("*.md")):
                if md.name.lower() != "index.md":
                    pages.append(md)
    return pages


def main() -> int:
    config_text = CONFIG.read_text(encoding="utf-8")
    missing = [_site_link(p) for p in _diataxis_pages() if _site_link(p) not in config_text]
    if missing:
        print("Pages missing from .vitepress/config.mts sidebar:")
        for link in missing:
            print(f"  - {link}")
        print("\nAdd each to sidebarEn()/sidebarJa() in .vitepress/config.mts.")
        return 1
    print("Sidebar coverage OK: every Diátaxis page is reachable from the nav.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
