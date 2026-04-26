#!/usr/bin/env python3
"""
Stage A + B + C of the DOI / ACL-Anthology-ID pipeline.

A. Parse the existing publications.yaml: pull DOIs and anthology IDs out of
   each entry's bibtex block and url fields.
B. Mine the Semantic Scholar cache (_data/citation_cache_s2.yaml) for
   externalIds.DOI and externalIds.ACL.
C. For papers still missing a DOI, query Crossref's /works endpoint by
   title+first-author. Auto-accept top results with title similarity >= 0.9
   and a verified author match. Borderline candidates are flagged for review.

Output:
  _data/doi_review.yaml — flat map: id -> {doi, anthology_id, doi_source,
  doi_confidence, notes, alternates(?)}.

Usage:
    /opt/homebrew/anaconda3/bin/python3 bin/extract_dois.py [--limit N]
"""

import argparse
import difflib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PUBS_PATH = ROOT / "_data" / "publications.yaml"
S2_PATH = ROOT / "_data" / "citation_cache_s2.yaml"
REVIEW_PATH = ROOT / "_data" / "doi_review.yaml"

CROSSREF_URL = "https://api.crossref.org/works"
USER_AGENT = "ccb-pubs-pipeline/0.1 (mailto:ccb@upenn.edu)"
TITLE_SIM_AUTO = 0.9
CROSSREF_DELAY_SEC = 0.2  # well below their 50/s polite cap

# ---- Pattern extraction --------------------------------------------------

# Match DOIs like 10.1145/3706598.3713716 or 10.18653/v1/D17-1001
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\}\"\)\,;]+)", re.IGNORECASE)

# ACL Anthology IDs come in two flavors:
#   - Pre-2020 alphanumeric:  P19-1001, D17-1001, W14-3302, N18-1001, etc.
#   - 2020+ year-prefixed:    2024.acl-long.123, 2025.findings-emnlp.42
ANTH_LEGACY_RE = re.compile(r"\b([A-Z]\d{2}-\d{4})\b")
ANTH_MODERN_RE = re.compile(r"\b(20\d{2}\.[a-z][a-z0-9\-]*\.\d+)\b")
ANTH_URL_RE = re.compile(
    r"aclanthology\.org/(20\d{2}\.[a-z][a-z0-9\-]*\.\d+|[A-Z]\d{2}-\d{4})/?",
    re.IGNORECASE,
)


def first_doi(text):
    if not text:
        return None
    m = DOI_RE.search(text)
    if not m:
        return None
    doi = m.group(1).rstrip(".,);")
    return doi


def first_anthology(text):
    if not text:
        return None
    m = ANTH_URL_RE.search(text)
    if m:
        return m.group(1)
    m = ANTH_MODERN_RE.search(text)
    if m:
        return m.group(1)
    m = ANTH_LEGACY_RE.search(text)
    if m:
        return m.group(1)
    return None


def doi_from_anthology(aid):
    """ACL DOIs since 2019 follow this deterministic pattern."""
    if not aid:
        return None
    # 2019+ uses 10.18653/v1/<aid>
    return f"10.18653/v1/{aid}"


def anthology_from_doi(doi):
    if not doi:
        return None
    if doi.startswith("10.18653/v1/"):
        return doi[len("10.18653/v1/"):]
    return None


def clean_title(t):
    if not t:
        return ""
    return t.replace("&colon;", ":").strip().strip('"').strip()


def first_author_lastname(authors_str):
    if not authors_str:
        return None
    first = authors_str.split(",")[0].strip()
    parts = first.split()
    if not parts:
        return None
    return parts[-1]


# ---- Crossref ------------------------------------------------------------


def crossref_search(title, author_lastname):
    params = {
        "query.bibliographic": title,
        "rows": "3",
        "select": "DOI,title,author,score,issued",
    }
    if author_lastname:
        params["query.author"] = author_lastname
    url = CROSSREF_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)[:140], "items": []}
    items = (data.get("message") or {}).get("items") or []
    return {"items": items}


def crossref_match(pub, title, author_lastname):
    res = crossref_search(title, author_lastname)
    if "error" in res and not res["items"]:
        return None, res["error"], []
    items = res["items"]
    if not items:
        return None, "no candidates", []
    # rank by title similarity
    ranked = []
    for it in items:
        cr_title = (it.get("title") or [""])[0]
        sim = difflib.SequenceMatcher(None, title.lower(), cr_title.lower()).ratio()
        cr_authors = " ".join(
            f"{a.get('given','')} {a.get('family','')}".strip()
            for a in (it.get("author") or [])
        ).lower()
        author_match = bool(author_lastname) and (
            author_lastname.lower() in cr_authors
        )
        ranked.append((sim, author_match, it, cr_title))
    ranked.sort(key=lambda x: (-x[0], -int(x[1])))
    top_sim, top_author, top, top_title = ranked[0]
    accept = top_sim >= TITLE_SIM_AUTO and top_author
    alts = [
        {
            "doi": r[2].get("DOI"),
            "title": r[3],
            "similarity": round(r[0], 3),
            "author_match": r[1],
        }
        for r in ranked
    ]
    return (
        {
            "doi": top.get("DOI"),
            "title": top_title,
            "similarity": round(top_sim, 3),
            "author_match": top_author,
            "auto_accept": accept,
        },
        None,
        alts,
    )


# ---- Main pipeline -------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--limit", type=int, help="Process only first N publications")
    ap.add_argument("--skip-crossref", action="store_true", help="Skip Stage C")
    args = ap.parse_args()

    pubs = yaml.safe_load(open(PUBS_PATH)) or []
    pubs = [p for p in pubs if isinstance(p, dict) and p.get("id")]
    if args.limit:
        pubs = pubs[: args.limit]

    s2_cache = {}
    if S2_PATH.exists():
        s2_cache = yaml.safe_load(open(S2_PATH)) or {}

    out = {}
    needs_crossref = []

    # ---- Stage A + B ----
    print(f"Stage A+B: parsing {len(pubs)} publications...")
    a_count = b_count = 0
    for pub in pubs:
        pid = pub["id"]
        bibtex = pub.get("bibtex") or ""
        url = pub.get("url") or ""
        haystack = bibtex + "\n" + url

        doi = first_doi(haystack)
        aid = first_anthology(haystack)
        source = []

        if doi or aid:
            a_count += 1
            if doi:
                source.append("bibtex/url")
            if aid and not doi:
                # try to derive doi from anthology id
                derived = doi_from_anthology(aid)
                if derived:
                    doi = derived
                    source.append("derived-from-anthology")

        # Stage B: S2 cache
        s2_entry = s2_cache.get(pid) or {}
        s2_ext = s2_entry.get("external_ids") or {}
        if not doi and s2_ext.get("DOI"):
            doi = s2_ext["DOI"]
            source.append("s2")
            b_count += 1
        if not aid and s2_ext.get("ACL"):
            aid = s2_ext["ACL"]
            if "s2" not in source:
                source.append("s2")
            b_count_was = True
        # If we have a DOI but no anthology id, see if doi gives us one
        if doi and not aid:
            derived_aid = anthology_from_doi(doi)
            if derived_aid:
                aid = derived_aid

        out[pid] = {
            "title": clean_title(pub.get("title")),
            "venue": pub.get("venue"),
            "year": pub.get("year"),
            "doi": doi,
            "anthology_id": aid,
            "doi_source": "+".join(source) if source else None,
            "doi_confidence": "high" if doi else "missing",
        }
        if not doi:
            needs_crossref.append(pid)

    print(f"  Found in bibtex/url:   {a_count}")
    print(f"  Added from S2 cache:   {b_count}")
    print(f"  Missing DOI after A+B: {len(needs_crossref)}")

    # ---- Stage C: Crossref ----
    if not args.skip_crossref and needs_crossref:
        print(f"\nStage C: Crossref lookup for {len(needs_crossref)} papers...")
        by_id = {p["id"]: p for p in pubs}
        for i, pid in enumerate(needs_crossref, 1):
            pub = by_id[pid]
            title = clean_title(pub.get("title"))
            author = first_author_lastname(pub.get("authors"))
            top, err, alts = crossref_match(pub, title, author)
            if top is None:
                out[pid]["doi_confidence"] = "missing"
                out[pid]["notes"] = f"crossref: {err}"
                print(f"  [{i:3}/{len(needs_crossref)}] {pid:42} no match ({err})")
            elif top["auto_accept"]:
                out[pid]["doi"] = top["doi"]
                out[pid]["doi_source"] = "crossref"
                out[pid]["doi_confidence"] = "high"
                out[pid]["doi_match_score"] = top["similarity"]
                out[pid]["doi_match_title"] = top["title"]
                # if it's an ACL DOI, derive anthology
                derived = anthology_from_doi(top["doi"])
                if derived and not out[pid].get("anthology_id"):
                    out[pid]["anthology_id"] = derived
                print(
                    f"  [{i:3}/{len(needs_crossref)}] {pid:42} "
                    f"{top['doi']:35} sim={top['similarity']:.2f}"
                )
            else:
                out[pid]["doi"] = None
                out[pid]["doi_confidence"] = "review"
                out[pid]["doi_alternates"] = alts
                print(
                    f"  [{i:3}/{len(needs_crossref)}] {pid:42} "
                    f"REVIEW: top sim={top['similarity']:.2f} author_match={top['author_match']}"
                )
            time.sleep(CROSSREF_DELAY_SEC)

    # ---- Save review file ----
    with open(REVIEW_PATH, "w", encoding="utf-8") as f:
        f.write(
            "# Auto-generated by bin/extract_dois.py — review and apply with bin/apply_dois.py.\n"
            f"# Generated {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}.\n"
        )
        yaml.safe_dump(out, f, sort_keys=True, allow_unicode=True, default_flow_style=False)

    # ---- Summary ----
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    by_status = {}
    with_anth = 0
    for v in out.values():
        by_status[v["doi_confidence"]] = by_status.get(v["doi_confidence"], 0) + 1
        if v.get("anthology_id"):
            with_anth += 1
    for k, n in sorted(by_status.items()):
        print(f"  doi_confidence={k:8}  {n}")
    print(f"  with anthology_id:  {with_anth}")
    print(f"\nReview file: {REVIEW_PATH}")
    print(f"Total papers in review: {len(out)}")


if __name__ == "__main__":
    main()
