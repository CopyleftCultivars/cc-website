"""Fetch the numbers shown on the Facts page from public APIs.

Writes data/facts.json and _facts_table.md (included by facts.qmd). Standard library only,
no tokens. Every fact records its value, the public URL it came from, the API field, and
when it was fetched.

This script never fails the build. If a fetch fails, or a value falls outside its sanity
range, the last committed value is kept and marked with `stale_since`. It always exits 0.

Usage: python3 scripts/build_facts.py
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "data" / "facts.json"
TABLE = ROOT / "_facts_table.md"

HF_ORG = "CopyleftCultivars"
GH_ORG = "CopyleftCultivars"
MCP_RAW = "https://raw.githubusercontent.com/CopyleftCultivars/cultivars-mcp/main"

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "cc-website-facts/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8")
    return body if raw else json.loads(body)


def public(items):
    return [x for x in items if not x.get("private")]


# Each fact: key -> (label, page URL a reader can check, API field, fetch function, check).
# The fetch function returns the value; the check returns True if the value is plausible.

def hf_list(kind):
    url = (f"https://huggingface.co/api/{kind}?author={HF_ORG}&limit=1000"
           "&expand[]=downloads&expand[]=downloadsAllTime&expand[]=private&expand[]=lastModified")
    return public(get(url))


_cache = {}


def cached(name, fn):
    if name not in _cache:
        _cache[name] = fn()
    return _cache[name]


def models():
    return cached("models", lambda: hf_list("models"))


def datasets():
    return cached("datasets", lambda: hf_list("datasets"))


def top_dataset():
    d = max(datasets(), key=lambda x: x.get("downloadsAllTime", 0))
    return {"name": d["id"].split("/", 1)[1], "downloads_all_time": d["downloadsAllTime"]}


def mcp_server():
    return cached("server", lambda: get(f"{MCP_RAW}/server.py", raw=True))


def mcp_data_sources():
    readme = cached("readme", lambda: get(f"{MCP_RAW}/README.md", raw=True))
    section = readme.split("## Data sources", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^- \*\*\[([^\]]+)\]", section, re.M)


def latest_ci():
    runs = get(f"https://api.github.com/repos/{GH_ORG}/cultivars-mcp/actions/workflows/ci.yml/runs"
               "?branch=main&status=completed&per_page=1")["workflow_runs"]
    return runs[0]


def is_count(lo, hi):
    return lambda v: isinstance(v, int) and lo <= v <= hi


def is_date(v):
    return isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) is not None


FACTS_SPEC = {
    "hf_models": (
        "Public models on Hugging Face",
        f"https://huggingface.co/{HF_ORG}", "count of /api/models?author=",
        lambda: len(models()), is_count(1, 1000)),
    "hf_datasets": (
        "Public datasets on Hugging Face",
        f"https://huggingface.co/{HF_ORG}", "count of /api/datasets?author=",
        lambda: len(datasets()), is_count(1, 1000)),
    "hf_downloads_all_time": (
        "Downloads of those models and datasets, all time",
        f"https://huggingface.co/{HF_ORG}", "sum of downloadsAllTime",
        lambda: sum(x.get("downloadsAllTime", 0) for x in models() + datasets()),
        is_count(0, 10**9)),
    "hf_downloads_30d": (
        "Downloads of those models and datasets, last 30 days",
        f"https://huggingface.co/{HF_ORG}", "sum of downloads",
        lambda: sum(x.get("downloads", 0) for x in models() + datasets()),
        is_count(0, 10**9)),
    "hf_top_dataset": (
        "Most-downloaded dataset, all time",
        None, "max downloadsAllTime over datasets",
        top_dataset,
        lambda v: isinstance(v, dict) and is_count(0, 10**9)(v.get("downloads_all_time"))),
    "hf_followers": (
        "Followers of the Hugging Face organization",
        f"https://huggingface.co/{HF_ORG}", "numFollowers",
        lambda: get(f"https://huggingface.co/api/organizations/{HF_ORG}/overview")["numFollowers"],
        is_count(0, 10**7)),
    "gh_public_repos": (
        "Public repositories on GitHub",
        f"https://github.com/{GH_ORG}", "public_repos",
        lambda: get(f"https://api.github.com/orgs/{GH_ORG}")["public_repos"],
        is_count(1, 1000)),
    "mcp_tools": (
        "Tools in Cultivars MCP",
        "https://github.com/CopyleftCultivars/cultivars-mcp/blob/main/server.py",
        "count of @mcp.tool in server.py",
        lambda: len(re.findall(r"^@mcp\.tool", mcp_server(), re.M)),
        is_count(1, 1000)),
    "mcp_unit_tests": (
        "Unit tests in Cultivars MCP",
        "https://github.com/CopyleftCultivars/cultivars-mcp/blob/main/tests/test_server.py",
        "count of def test_ in tests/test_server.py",
        lambda: len(re.findall(r"^\s*(?:async )?def test_",
                               get(f"{MCP_RAW}/tests/test_server.py", raw=True), re.M)),
        is_count(1, 100000)),
    "mcp_ci": (
        "Cultivars MCP tests on the main branch, latest CI run",
        None, "conclusion of the latest completed ci.yml run on main",
        lambda: {k: v for k, v in latest_ci().items() if k in ("conclusion", "html_url", "updated_at")},
        lambda v: isinstance(v, dict) and v.get("conclusion") in ("success", "failure")),
    "mcp_data_sources": (
        "Public databases Cultivars MCP works with",
        "https://github.com/CopyleftCultivars/cultivars-mcp#data-sources",
        "bulleted names under ## Data sources in README.md",
        mcp_data_sources,
        lambda v: isinstance(v, list) and 1 <= len(v) <= 100),
    "updated_cultivars_mcp": (
        "Cultivars MCP code, last updated",
        "https://github.com/CopyleftCultivars/cultivars-mcp", "pushed_at",
        lambda: get(f"https://api.github.com/repos/{GH_ORG}/cultivars-mcp")["pushed_at"][:10],
        is_date),
    "updated_agri_vision_detector": (
        "AgriVision plant-health detector model, last updated",
        f"https://huggingface.co/{HF_ORG}/agri-vision-detector", "lastModified",
        lambda: get(f"https://huggingface.co/api/models/{HF_ORG}/agri-vision-detector")["lastModified"][:10],
        is_date),
    "updated_agri_vision_space": (
        "AgriVision demo Space, last updated",
        f"https://huggingface.co/spaces/{HF_ORG}/agri-vision", "lastModified",
        lambda: get(f"https://huggingface.co/api/spaces/{HF_ORG}/agri-vision")["lastModified"][:10],
        is_date),
    "updated_farming_model": (
        "Natural farming model (Qwen3.5 2B, v5), last updated",
        f"https://huggingface.co/{HF_ORG}/qwen3.5-2b-natural-farming-v5", "lastModified",
        lambda: get(f"https://huggingface.co/api/models/{HF_ORG}/qwen3.5-2b-natural-farming-v5")["lastModified"][:10],
        is_date),
}


def source_url(key, spec_url, value):
    if key == "hf_top_dataset" and isinstance(value, dict):
        return f"https://huggingface.co/datasets/{HF_ORG}/{value['name']}"
    if key == "mcp_ci" and isinstance(value, dict):
        return value.get("html_url")
    return spec_url


def collect(old):
    facts, fresh, stale, missing = {}, 0, [], []
    for key, (label, url, field, fetch, ok) in FACTS_SPEC.items():
        try:
            value = fetch()
            if not ok(value):
                raise ValueError(f"value outside sanity range: {value!r}")
            facts[key] = {"label": label, "value": value, "source_url": source_url(key, url, value),
                          "field": field, "fetched_at": NOW}
            fresh += 1
        except Exception as e:  # noqa: BLE001 - any failure falls back to the last value
            prev = old.get(key)
            if prev:
                prev = dict(prev)
                prev.setdefault("stale_since", NOW)
                prev["last_error"] = f"{type(e).__name__}: {e}"[:200]
                facts[key] = prev
                stale.append(f"{key} ({type(e).__name__})")
            else:
                missing.append(f"{key} ({type(e).__name__})")
    return facts, fresh, stale, missing


def nice_date(iso):
    return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%-d %b %Y")


def fmt_value(key, v):
    if key == "hf_top_dataset":
        return f"{v['name']} ({v['downloads_all_time']:,} downloads)"
    if key == "mcp_ci":
        word = {"success": "passing", "failure": "failing"}[v["conclusion"]]
        return f"{word} ({nice_date(v['updated_at'])})"
    if key == "mcp_data_sources":
        return f"{len(v)}: " + ", ".join(v)
    if isinstance(v, int):
        return f"{v:,}"
    if is_date(v):
        return nice_date(v)
    return str(v)


def write_table(facts):
    lines = ["| Fact | Value | Source |", "|---|---|---|"]
    for key in FACTS_SPEC:
        f = facts.get(key)
        if not f:
            continue
        value = fmt_value(key, f["value"])
        if f.get("stale_since"):
            value += f" (as of {nice_date(f['fetched_at'])}, could not refresh)"
        host = "GitHub" if "github.com" in f["source_url"] else "Hugging&nbsp;Face"
        lines.append(f"| {f['label']} | {value} | [{host}]({f['source_url']}) |")
    if facts:
        newest = max(f["fetched_at"] for f in facts.values())
        lines += ["", f"Last updated {nice_date(newest)}."]
    else:
        lines = ["The numbers could not be fetched for this build. They will appear after the next one."]
    TABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    try:
        old = json.loads(FACTS.read_text(encoding="utf-8")).get("facts", {})
    except Exception:  # noqa: BLE001 - no committed file yet, or unreadable
        old = {}
    facts, fresh, stale, missing = collect(old)
    try:
        FACTS.parent.mkdir(parents=True, exist_ok=True)
        FACTS.write_text(json.dumps({"generated_at": NOW, "facts": facts}, indent=2,
                                    ensure_ascii=False) + "\n", encoding="utf-8")
        write_table(facts)
    except Exception as e:  # noqa: BLE001 - never fail the build
        print(f"build_facts: could not write output: {e}")
    print(f"build_facts: {fresh} fresh, {len(stale)} kept from last run, {len(missing)} unavailable")
    for label, items in (("kept", stale), ("unavailable", missing)):
        if items:
            print(f"  {label}: " + ", ".join(items))
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 - never fail the build
        print(f"build_facts: unexpected error, page keeps the committed numbers: {e}")
    sys.exit(0)
