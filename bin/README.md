# Citation & Bibliometrics Pipeline

Scripts in this directory pull citation counts from Google Scholar (via SerpAPI)
and Semantic Scholar, attach DOIs and ACL Anthology IDs to publications, and
compute bibliometrics (h-index, i10, etc.) for use on the site.

All scripts are stand-alone and only need Python 3 + `pyyaml`. On this machine
use `/opt/homebrew/anaconda3/bin/python3` because the system Python is
externally-managed by `uv`.

## Quick reference

```bash
# Refresh citation counts (Google Scholar via SerpAPI)
SERPAPI_KEY=… /opt/homebrew/anaconda3/bin/python3 bin/update_citations.py

# Refresh citation counts (Semantic Scholar)
S2_API_KEY=…  /opt/homebrew/anaconda3/bin/python3 bin/update_citations_s2.py

# Recompute bibliometrics (h-index, i10, etc.) from the caches above
/opt/homebrew/anaconda3/bin/python3 bin/bibliometrics.py
```

After any of these run, the corresponding `_data/*.yaml` file is updated and
Jekyll will pick it up on the next build.

## Files

### Scripts

| Script | Purpose |
|---|---|
| `update_citations.py` | Google Scholar citation counts via SerpAPI. Caches to `_data/citation_cache.yaml`. |
| `update_citations_s2.py` | Semantic Scholar citation counts via S2 Graph API. Lookup priority: DOI → arXiv → title. Caches to `_data/citation_cache_s2.yaml`. |
| `extract_dois.py` | Mines DOIs and ACL Anthology IDs from existing bibtex/URLs, then S2 cache, then Crossref. Writes `_data/doi_review.yaml`. |
| `apply_dois.py` | Inserts the DOIs from `doi_review.yaml` into `publications.yaml` as new top-level fields. |
| `bibliometrics.py` | Computes h-index, g-index, i10/i100, and top-10 lists from both citation caches. Writes `_data/bibliometrics.yaml`. |

### Data files (auto-generated, safe to commit)

| File | What it holds |
|---|---|
| `_data/citation_cache.yaml` | Google Scholar citation counts, keyed by publication `id`. |
| `_data/citation_cache_s2.yaml` | Semantic Scholar citation counts (regular + influential). |
| `_data/bibliometrics.yaml` | Computed h-index, totals, top-10 lists, etc. |
| `_data/doi_review.yaml` | Provenance: where each DOI came from (bibtex, S2, Crossref, subagent). |

### Data files (hand-maintained — DO NOT regenerate)

- `_data/publications.yaml` — the canonical publications list. The pipeline only
  edits it once via `apply_dois.py` to add `doi:` and `anthology_id:` fields per
  entry. Format is hand-curated; never round-trip it through `yaml.safe_dump`.

## API keys

Stored as environment variables, **never committed**.

```bash
export SERPAPI_KEY=…   # https://serpapi.com/manage-api-key
export S2_API_KEY=…    # https://www.semanticscholar.org/product/api
```

The user's existing keys for this project:

- **SerpAPI**: `4665d84f50f140a2c9dfe0e99cdfee04c96196f937e7a5ffb5235a1b6ddc4c33` (~250 free searches/month, paid tiers higher)
- **Semantic Scholar**: `s2k-mZ98t1UfZYBpaa91o6R80SXSmgNC7asth7WCsOPr` (1 request/second; sustained throttling triggers backoff)

## Routine workflow: refresh the numbers on the site

1. Run the two citation refreshers. They use a 7-day freshness check, so
   re-running within a week is a no-op (free).
   ```bash
   SERPAPI_KEY=…  /opt/homebrew/anaconda3/bin/python3 bin/update_citations.py
   S2_API_KEY=…   /opt/homebrew/anaconda3/bin/python3 bin/update_citations_s2.py
   ```
2. Recompute bibliometrics:
   ```bash
   /opt/homebrew/anaconda3/bin/python3 bin/bibliometrics.py
   ```
3. Commit the four updated `_data/*.yaml` files.

Total cost: ~280 SerpAPI credits + ~280 S2 calls + ~10 minutes.

To force a refresh on already-cached entries, add `--force`. To do a small spot
check first:

```bash
# 5 random papers, ignoring cache freshness
… update_citations.py --sample 5 --seed 42 --force

# A single paper by id
… update_citations_s2.py --id molmo --force
```

## Routine workflow: add a new publication

1. Add the entry to `_data/publications.yaml` by hand.
2. Refresh citations for just that paper:
   ```bash
   SERPAPI_KEY=… /opt/homebrew/anaconda3/bin/python3 bin/update_citations.py --id <new-id>
   S2_API_KEY=…  /opt/homebrew/anaconda3/bin/python3 bin/update_citations_s2.py --id <new-id>
   ```
3. If the new entry has a DOI in its bibtex, copy it into the entry's
   top-level `doi:` field by hand (or re-run the DOI pipeline — see below).
4. Recompute bibliometrics.

## Adding DOIs to entries (one-time / occasional)

The `extract_dois.py` + `apply_dois.py` pipeline was a one-shot run that has
already populated `doi:` and `anthology_id:` on every existing entry. New
entries don't get them automatically. If you want them, re-run:

```bash
# Stage A+B+C: parse bibtex/URLs, then S2 cache, then Crossref.
/opt/homebrew/anaconda3/bin/python3 bin/extract_dois.py

# Review _data/doi_review.yaml. Hand-edit any incorrect picks.
# Then write into publications.yaml:
/opt/homebrew/anaconda3/bin/python3 bin/apply_dois.py             # dry run
/opt/homebrew/anaconda3/bin/python3 bin/apply_dois.py --apply
```

`apply_dois.py` only adds fields that are not already present in the entry, so
re-running is safe. Pass `--overwrite` to replace existing values.

### DOI conventions in `publications.yaml`

| Value | Meaning |
|---|---|
| `doi: 10.x/y` | Real DOI. |
| `doi: null` | Confirmed no DOI exists (theses, podcasts, pre-DOI workshops). Don't recheck. |
| `doi: pending` | Paper exists, DOI doesn't yet (forthcoming venue). Re-check on future runs. |
| field absent | Never tried. |

For Liquid display, hide pending DOIs:
```liquid
{% if pub.doi and pub.doi != "pending" %}…{% endif %}
```

## Fixing a wrong citation match

If `bin/bibliometrics.py` shows an obviously wrong top paper (e.g. a 5-figure
citation count for a small workshop piece), the culprit is usually a bad title
match. To clear it:

```yaml
# Open _data/citation_cache.yaml or _data/citation_cache_s2.yaml.
# Find the offending id and edit it in place:
some-paper-id:
  citation_count: null
  citation_count_updated: '2026-04-25T00:00:00+00:00'
  match_confidence: none
  notes: wrong match — Manning & Schutze textbook. Cleared manually.
```

Then re-run `bibliometrics.py`.

To re-fetch a single paper after editing:
```bash
… update_citations.py --id <paper-id> --force
```

## Liquid integration

`_data/*.yaml` files are loaded by Jekyll as `site.data.<filename>`.

```liquid
{# Citation count on a single publication #}
{% assign gs = site.data.citation_cache[pub.id] %}
{% assign s2 = site.data.citation_cache_s2[pub.id] %}
{% if gs.citation_count %}
  Cited {{ gs.citation_count }} times (Google Scholar).
{% endif %}

{# Aggregate stats #}
{{ site.data.bibliometrics.google_scholar.h_index }}
{{ site.data.bibliometrics.semantic_scholar.h_index }}
{{ site.data.bibliometrics.google_scholar.total_citations }}
```

Any time you display Semantic Scholar data, S2's terms ask for attribution:

```html
<small>
  Citation counts via
  <a href="https://www.semanticscholar.org/">Semantic Scholar</a>
  and Google Scholar (SerpAPI).
</small>
```

## Troubleshooting

### Semantic Scholar returns 429 (too many requests)

The S2 free key is 1 req/s **cumulative across all endpoints**. Sustained load
sometimes triggers a sliding-window throttle that takes minutes to clear. The
script has built-in exponential backoff (10s → 20s → 40s → 80s) so 429s
auto-recover, just slowly. If a full refresh takes 30+ minutes instead of 10,
that's why.

If you hit a hard wall, wait a few minutes and re-run without `--force` — only
the un-cached entries will be retried.

### A paper has no S2 match

Some papers aren't indexed by S2 (workshop-only, recent preprints, podcasts).
The cache will have `match_confidence: none` and `citation_count: null` for
those. They're correctly excluded from the bibliometrics computation.

### A paper has the wrong DOI in publications.yaml

Edit `_data/publications.yaml` directly. The pipeline won't overwrite an
existing `doi:` field on subsequent runs unless you pass `--overwrite` to
`apply_dois.py`.

### I want to see how a DOI was decided

Open `_data/doi_review.yaml` and look up the paper id. Each entry has
`doi_source` (e.g. `bibtex/url`, `s2`, `crossref`, `subagent`, `arxiv-derived`)
and `notes` describing the decision.

### Throwing away the citation cache

Delete `_data/citation_cache.yaml` (or the S2 one) and re-run. The next run
rebuilds it from scratch, costing ~280 API credits per cache.

## Cost notes

- **SerpAPI** is metered. Each Google Scholar query uses 1 search credit.
  A full refresh is ~280 credits. Free tier was 250/month last I checked.
- **Semantic Scholar** is free with the API key, but rate-limited.
- **Crossref** is free; no key needed; their polite cap is ~50 req/s and we use
  ~5 req/s to be safe.

## Why a sidecar cache instead of inline `citation_count` fields?

`publications.yaml` is hand-curated with idiosyncratic formatting (mixed 2/3
space indents, `&colon;` escapes, multi-line literal `|` bibtex blocks). Any
round-trip through `pyyaml` would obliterate this format. Sidecar cache files
are auto-generated, regenerable, and join with `publications.yaml` at render
time via the publication's `id`. The DOI / anthology ID fields are the
exception: those are added once via line-level surgical inserts in
`apply_dois.py` and then maintained by hand.
