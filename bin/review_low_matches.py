#!/usr/bin/env python3
"""One-shot cleanup script for low/none matches in the citation cache.

- Upgrades cache entries with title_similarity >= 0.95 and match_confidence='low' to 'high'.
- Clears the known-bad match for statistical-natural-language-processing-chapter.
- Re-queries the three WMT findings papers with quoted year-specific titles.
- Re-queries the crowdsourced-translation paper (yaml typo now fixed).
- Fetches top-5 Scholar alternates for the remaining problem papers and
  prints a human-readable picklist the user can respond to.

Usage:
    export SERPAPI_KEY=...
    /opt/homebrew/anaconda3/bin/python3 bin/review_low_matches.py
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PUB_PATH = ROOT / "_data" / "publications.yaml"
CACHE_PATH = ROOT / "_data" / "citation_cache.yaml"
SERPAPI_URL = "https://serpapi.com/search.json"

# Entries to handle specially: {paper_id: scholar_query}
RE_QUERY = {
    "findings-of-the-wmt09-shared-tasks": '"Findings of the 2009 Workshop on Statistical Machine Translation"',
    "findings-of-the-wmt12-shared-tasks": '"Findings of the 2012 Workshop on Statistical Machine Translation"',
    "findings-of-the-wmt13-shared-tasks": '"Findings of the 2013 Workshop on Statistical Machine Translation"',
    "crowdsourced-translation-via-collaboration-between-translators-and-editors": (
        '"Are Two Heads Better than One? Crowdsourced Translation via a Two-Step '
        'Collaboration between Translators and Editors"'
    ),
}

# Fetch top-5 alternates for these. Query with the yaml title.
PICKLIST_IDS = [
    "statistical-natural-language-processing-chapter",
    "hiero-grammar-extraction-with-suffix-arrays",
    "searchable-translation-memories",
    "cost-optimization-for-crowdsourcing-translation",
    "gvdb-d4gx",
    "human-ai-cooperation-healthcare",
    "domain-specific-paraphrases",
    "shield-of-heroic-memories",
    "llms-and-corpora",
]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def query_scholar(q, api_key):
    params = {"engine": "google_scholar", "q": q, "api_key": api_key}
    url = SERPAPI_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compact_result(r):
    cited = (r.get("inline_links") or {}).get("cited_by") or {}
    return {
        "title": r.get("title"),
        "snippet": r.get("snippet"),
        "summary": ((r.get("publication_info") or {}).get("summary") or "")[:200],
        "cited_by": cited.get("total"),
        "cluster_id": cited.get("cites_id"),
        "result_id": r.get("result_id"),
        "link": r.get("link"),
    }


def main():
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        sys.exit("Set SERPAPI_KEY")

    cache = yaml.safe_load(open(CACHE_PATH)) or {}
    pubs = yaml.safe_load(open(PUB_PATH)) or []
    by_id = {p["id"]: p for p in pubs if isinstance(p, dict) and p.get("id")}

    # Step 1: bulk-approve sim >= 0.95, low -> high
    upgraded = 0
    for pid, entry in cache.items():
        if (
            entry.get("match_confidence") == "low"
            and (entry.get("title_similarity") or 0) >= 0.95
        ):
            entry["match_confidence"] = "high"
            entry["notes"] = "bulk-approved: title_similarity>=0.95"
            upgraded += 1
    print(f"Step 1: upgraded {upgraded} entries from low->high (title_sim>=0.95)")

    # Step 2: clear the known bad Manning & Schutze match
    if "statistical-natural-language-processing-chapter" in cache:
        bad = cache["statistical-natural-language-processing-chapter"]
        bad["citation_count"] = None
        bad["match_confidence"] = "none"
        bad["notes"] = "wrong match (Manning & Schutze textbook); cleared"
        print("Step 2: cleared bad match on statistical-natural-language-processing-chapter")

    # Step 3 + 4: re-query specific papers
    for pid, q in RE_QUERY.items():
        pub = by_id.get(pid)
        if not pub:
            print(f"  skip re-query: no publication id={pid}")
            continue
        print(f"Step 3/4: re-querying {pid}  q={q[:70]}...")
        try:
            data = query_scholar(q, api_key)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        results = data.get("organic_results") or []
        if not results:
            cache.setdefault(pid, {}).update(
                {
                    "citation_count": None,
                    "citation_count_updated": now_iso(),
                    "match_confidence": "none",
                    "notes": f"re-query returned no results: {q}",
                }
            )
            continue
        top = results[0]
        cited = (top.get("inline_links") or {}).get("cited_by") or {}
        count = cited.get("total") if "total" in cited else (0 if cited else None)
        cache[pid] = {
            "citation_count": count,
            "citation_count_updated": now_iso(),
            "scholar_cluster_id": cited.get("cites_id"),
            "scholar_result_id": top.get("result_id"),
            "scholar_result_title": top.get("title"),
            "match_confidence": "high",
            "title_similarity": 1.0,
            "notes": f"re-queried with quoted title: {q[:80]}",
        }
        print(f"  -> {top.get('title')[:70]}  cites={count}")
        time.sleep(1)

    # Step 5: fetch top-5 alternates for the remaining problem papers
    picklist = {}
    for pid in PICKLIST_IDS:
        pub = by_id.get(pid)
        if not pub:
            continue
        title = (pub.get("title") or "").replace("&colon;", ":").strip().strip('"')
        print(f"\nStep 5: fetching alternates for {pid}...")
        try:
            data = query_scholar(title, api_key)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        results = (data.get("organic_results") or [])[:5]
        picklist[pid] = {
            "yaml_title": title,
            "yaml_authors": pub.get("authors"),
            "yaml_venue": pub.get("venue"),
            "yaml_year": pub.get("year"),
            "alternates": [compact_result(r) for r in results],
        }
        time.sleep(1)

    # Save the updated cache
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        f.write(
            "# Auto-generated by bin/update_citations.py — do not edit by hand.\n"
            "# Citation counts and match metadata from Google Scholar (via SerpAPI),\n"
            "# keyed by publication id from _data/publications.yaml.\n"
        )
        yaml.safe_dump(cache, f, sort_keys=True, allow_unicode=True, default_flow_style=False)

    # Save the picklist
    picklist_path = ROOT / "_data" / "citation_review_picklist.yaml"
    with open(picklist_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(picklist, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

    print(f"\nCache saved. Picklist at {picklist_path}")
    print()
    print("=" * 100)
    print("PICKLIST for user review:")
    print("=" * 100)
    for pid, d in picklist.items():
        print(f"\n### {pid}")
        print(f"    yaml title:   {d['yaml_title']}")
        print(f"    yaml authors: {d['yaml_authors']}")
        print(f"    yaml venue:   {d['yaml_venue']} ({d['yaml_year']})")
        alts = d["alternates"]
        if not alts:
            print("    (no Scholar results)")
            continue
        for i, a in enumerate(alts, 1):
            summary = a.get("summary") or ""
            print(f"    [{i}] {a['title']}")
            print(f"        {summary[:120]}")
            print(f"        cites={a['cited_by']}  cluster={a['cluster_id']}  link={a['link']}")
    print()
    print(
        "To apply your picks, tell Claude e.g.:\n"
        "  hiero-grammar-extraction-with-suffix-arrays: 1\n"
        "  searchable-translation-memories: 2\n"
        "  llms-and-corpora: none\n"
    )


if __name__ == "__main__":
    main()
