#!/usr/bin/env python3
"""
Compute bibliometrics from the citation caches and write them to
_data/bibliometrics.yaml for use in Liquid templates.

Computes (per source):
  - total publications (with a citation count)
  - total citations
  - mean / median citations per paper
  - h-index   = largest h such that >=h papers each have >=h citations
  - g-index   = largest g such that the top g papers have >=g^2 total cites
  - i10-index = number of papers with >=10 citations
  - i100-index = number of papers with >=100 citations (rough "high impact")
  - top 10 papers by citation count

Semantic Scholar additionally exposes:
  - influential_citation_count — sum, mean, top 10
  - h-index based on influential citation counts

Usage:
    /opt/homebrew/anaconda3/bin/python3 bin/bibliometrics.py
"""

import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GS_PATH = ROOT / "_data" / "citation_cache.yaml"
S2_PATH = ROOT / "_data" / "citation_cache_s2.yaml"
PUB_PATH = ROOT / "_data" / "publications.yaml"
OUT_PATH = ROOT / "_data" / "bibliometrics.yaml"


def h_index(counts):
    counts = sorted([c for c in counts if c is not None], reverse=True)
    h = 0
    for i, c in enumerate(counts, 1):
        if c >= i:
            h = i
        else:
            break
    return h


def g_index(counts):
    counts = sorted([c for c in counts if c is not None], reverse=True)
    cumulative = 0
    g = 0
    for i, c in enumerate(counts, 1):
        cumulative += c
        if cumulative >= i * i:
            g = i
        else:
            break
    return g


def i_n_index(counts, n):
    return sum(1 for c in counts if c is not None and c >= n)


def compute(counts):
    counts = [c for c in counts if c is not None]
    if not counts:
        return {
            "papers_with_count": 0,
            "total_citations": 0,
            "mean": 0.0,
            "median": 0.0,
            "h_index": 0,
            "g_index": 0,
            "i10_index": 0,
            "i100_index": 0,
        }
    return {
        "papers_with_count": len(counts),
        "total_citations": sum(counts),
        "mean": round(statistics.mean(counts), 1),
        "median": int(statistics.median(counts)),
        "h_index": h_index(counts),
        "g_index": g_index(counts),
        "i10_index": i_n_index(counts, 10),
        "i100_index": i_n_index(counts, 100),
    }


def top_n(items_with_count, n):
    """Return top-n entries from [(id, title, count), ...]."""
    items = [x for x in items_with_count if x[2] is not None]
    items.sort(key=lambda x: -x[2])
    return [{"id": k, "title": t, "count": c} for k, t, c in items[:n]]


def main():
    pubs = {p["id"]: p for p in (yaml.safe_load(open(PUB_PATH)) or [])
            if isinstance(p, dict) and p.get("id")}
    skipped = {pid for pid, p in pubs.items() if p.get("skip_scholar")}

    gs = yaml.safe_load(open(GS_PATH)) or {} if GS_PATH.exists() else {}
    s2 = yaml.safe_load(open(S2_PATH)) or {} if S2_PATH.exists() else {}

    def dedupe_by(cache, key_field):
        """Keep one entry per external cluster id. When duplicates exist (Scholar
        merging near-identical titles), prefer the one whose pub_id sorts first
        for determinism. Pubs without a cluster id pass through unchanged."""
        by_key, kept = {}, {}
        for pid, e in sorted(cache.items()):
            if pid in skipped:
                continue
            k = e.get(key_field)
            if not k:
                kept[pid] = e
            elif k not in by_key:
                by_key[k] = pid
                kept[pid] = e
        return kept

    gs = dedupe_by(gs, "scholar_cluster_id")
    s2 = dedupe_by(s2, "s2_paper_id")

    # Build (id, title, count) lists
    gs_items = []
    for pid, e in gs.items():
        title = (pubs.get(pid, {}).get("title") or "").replace("&colon;", ":")
        gs_items.append((pid, title, e.get("citation_count")))
    s2_items = []
    s2_inf_items = []
    for pid, e in s2.items():
        title = (pubs.get(pid, {}).get("title") or "").replace("&colon;", ":")
        s2_items.append((pid, title, e.get("citation_count")))
        s2_inf_items.append((pid, title, e.get("influential_citation_count")))

    gs_counts = [x[2] for x in gs_items]
    s2_counts = [x[2] for x in s2_items]
    s2_inf_counts = [x[2] for x in s2_inf_items]

    output = {
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "google_scholar": {
            **compute(gs_counts),
            "top10": top_n(gs_items, 10),
        },
        "semantic_scholar": {
            **compute(s2_counts),
            "top10": top_n(s2_items, 10),
            "influential": {
                **compute(s2_inf_counts),
                "top10": top_n(s2_inf_items, 10),
            },
        },
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("# Auto-generated by bin/bibliometrics.py — recompute with that script.\n")
        yaml.safe_dump(output, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

    # Pretty-print to stdout
    def pp(label, d):
        print(f"\n=== {label} ===")
        print(f"  papers w/ count:   {d['papers_with_count']}")
        print(f"  total citations:   {d['total_citations']:,}")
        print(f"  mean / median:     {d['mean']} / {d['median']}")
        print(f"  h-index:           {d['h_index']}")
        print(f"  g-index:           {d['g_index']}")
        print(f"  i10-index:         {d['i10_index']}")
        print(f"  i100-index:        {d['i100_index']}")

    print(f"Generated: {output['generated']}")
    pp("Google Scholar", output["google_scholar"])
    pp("Semantic Scholar (citations)", output["semantic_scholar"])
    pp("Semantic Scholar (influential)", output["semantic_scholar"]["influential"])

    print("\n--- Top 10 by Google Scholar ---")
    for i, p in enumerate(output["google_scholar"]["top10"], 1):
        print(f"  {i:2}. {p['count']:>6}  {p['title'][:70]}")
    print("\n--- Top 10 by Semantic Scholar (influential) ---")
    for i, p in enumerate(output["semantic_scholar"]["influential"]["top10"], 1):
        print(f"  {i:2}. {p['count']:>4}  {p['title'][:70]}")

    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
