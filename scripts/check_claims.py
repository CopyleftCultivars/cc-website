"""Check the numbers in a draft (post, deck notes, grant text) against data/facts.json.

Finds numbers that sit next to words like downloads, tools, models, datasets, tests,
databases, repositories or followers, and reports any that don't match the facts file.
It is a helper for people writing; it is not part of the site build.

Usage: python3 scripts/check_claims.py DRAFT.txt [--facts data/facts.json]
Exit code 1 if any number disagrees with the facts file.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# word in the draft -> fact keys whose value that word can refer to
TOPICS = {
    r"downloads?": ["hf_downloads_all_time", "hf_downloads_30d", "hf_top_dataset"],
    r"tools?": ["mcp_tools"],
    r"models?": ["hf_models"],
    r"datasets?": ["hf_datasets"],
    r"(?:unit )?tests?": ["mcp_unit_tests"],
    r"(?:databases?|data sources?)": ["mcp_data_sources"],
    r"(?:repositories|repos)": ["gh_public_repos"],
    r"followers?": ["hf_followers"],
}

NUMBER = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([kK]\b|thousand\b)?"


def as_numbers(fact):
    v = fact["value"]
    if isinstance(v, int):
        return {v}
    if isinstance(v, list):
        return {len(v)}
    if isinstance(v, dict) and "downloads_all_time" in v:
        return {v["downloads_all_time"]}
    return set()


def parse(num, suffix):
    n = float(num.replace(",", ""))
    if suffix:
        n *= 1000
    return n


def matches(n, allowed, rounded):
    for a in allowed:
        if n == a:
            return True
        # "about 28k" or "28,000+" style rounding: accept within 5%, never above the real value
        if rounded and a and n <= a and (a - n) / a <= 0.05:
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Check numbers in a draft against data/facts.json")
    ap.add_argument("draft")
    ap.add_argument("--facts", default=str(ROOT / "data" / "facts.json"))
    args = ap.parse_args()

    facts = json.loads(Path(args.facts).read_text(encoding="utf-8"))["facts"]
    text = Path(args.draft).read_text(encoding="utf-8")
    problems = checked = 0

    for word, keys in TOPICS.items():
        allowed = set().union(*(as_numbers(facts[k]) for k in keys if k in facts))
        if not allowed:
            continue
        # a number followed by the topic word, with at most three plain words between
        pat = re.compile(NUMBER + r"(\+)?\s+(?:(?!and\b|or\b)[A-Za-z-]+\s+){0,3}?" + word + r"\b", re.I)
        for m in pat.finditer(text):
            n = parse(m.group(1), m.group(2))
            rounded = bool(m.group(2) or m.group(3))
            line = text.count("\n", 0, m.start()) + 1
            checked += 1
            if not matches(n, allowed, rounded):
                problems += 1
                want = ", ".join(f"{a:,}" for a in sorted(allowed))
                print(f"{args.draft}:{line}: '{m.group(0)}' does not match facts.json ({want})")

    print(f"{checked} numbers checked, {problems} disagree with {Path(args.facts).name}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
