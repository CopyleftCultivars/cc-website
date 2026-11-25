"""Fail if the Freedom Bag Tag page or the tag print text contains wording we don't use.

Checks preservation.qmd and tag-print/tag_text.txt for the old .com web address, blame
words about that address, and leftover placeholders such as [FILL ...].

Usage: python3 scripts/check_tag_page.py   (exit 1 on any finding)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [ROOT / "preservation.qmd", ROOT / "tag-print" / "tag_text.txt"]

PATTERNS = [
    ("old web address", re.compile(r"copyleftcultivars\.com", re.I)),
    ("blame word", re.compile(r"sniped|hijack|squatter", re.I)),
    ("ownership claim", re.compile(r"belongs to us", re.I)),
    ("placeholder", re.compile(r"\[(?:FILL|TODO|TBD|ADD|INSERT|PLACEHOLDER)\b", re.I)),
]


def main():
    found = 0
    for path in FILES:
        if not path.exists():
            print(f"missing: {path.relative_to(ROOT)}")
            found += 1
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for label, pat in PATTERNS:
                if pat.search(line):
                    print(f"{path.relative_to(ROOT)}:{n}: {label}: {line.strip()[:100]}")
                    found += 1
    if found:
        sys.exit(1)
    print(f"ok: {len(FILES)} files checked, nothing found")


if __name__ == "__main__":
    main()
