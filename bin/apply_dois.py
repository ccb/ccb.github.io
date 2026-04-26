#!/usr/bin/env python3
"""
Apply DOIs and ACL Anthology IDs from _data/doi_review.yaml back into
_data/publications.yaml as new top-level fields on each publication entry.

Insertion is line-based and surgical: for each `   id: <id>` line, we insert
`   doi: <value>` and `   anthology_id: <value>` lines immediately after,
preserving the entry's existing indentation. We never touch any other line.

If an entry already contains `doi:` or `anthology_id:` lines, those are
respected (we won't add a duplicate). To overwrite, pass --overwrite.

By default this is a dry run. Pass --apply to actually rewrite the file.

Usage:
    /opt/homebrew/anaconda3/bin/python3 bin/apply_dois.py            # dry run
    /opt/homebrew/anaconda3/bin/python3 bin/apply_dois.py --apply
    /opt/homebrew/anaconda3/bin/python3 bin/apply_dois.py --apply --overwrite
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PUB_PATH = ROOT / "_data" / "publications.yaml"
REVIEW_PATH = ROOT / "_data" / "doi_review.yaml"

ID_RE = re.compile(r"^(\s+)id:\s*(\S+)\s*$")
SEPARATOR_RE = re.compile(r"^-\s*$")
INLINE_LIST_START_RE = re.compile(r"^-\s+\S+:")  # e.g.  - title: "..."


def yaml_value(v):
    """Render a value the way we want it inline in publications.yaml."""
    if v is None:
        return "null"
    s = str(v)
    # Quote if there's a colon or other YAML-tricky chars
    if any(c in s for c in [":", "#", "&", "*", "!", "|", ">", "%", "@", "`", "'"]):
        return '"' + s.replace('"', r'\"') + '"'
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write changes (else dry run)")
    ap.add_argument("--overwrite", action="store_true", help="Replace existing doi/anthology_id lines")
    ap.add_argument("--limit", type=int, help="Only apply for the first N matching entries")
    args = ap.parse_args()

    review = yaml.safe_load(open(REVIEW_PATH)) or {}

    with open(PUB_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out = []
    in_entry = False
    entry_indent = ""
    entry_id = None
    entry_existing = set()  # field names already in the current entry
    entry_start_idx = -1
    pending_inserts = {}  # idx -> [lines to insert before that idx (1-based out length)]

    # Two-pass: first identify each entry's id-line index and existing fields
    # so we know whether to insert or skip per field.
    n = len(lines)
    i = 0
    entries = []  # list of {id_idx, indent, id, existing_fields, end_idx}
    cur = None
    field_re = re.compile(r"^(\s+)([A-Za-z_][A-Za-z0-9_]*):")
    while i < n:
        line = lines[i]
        starts_entry = SEPARATOR_RE.match(line) or INLINE_LIST_START_RE.match(line)
        if starts_entry:
            if cur is not None:
                cur["end_idx"] = i
                entries.append(cur)
            cur = {"id_idx": None, "indent": None, "id": None, "existing_fields": set(), "end_idx": None}
            # If inline form, the first field is on this same line
            if INLINE_LIST_START_RE.match(line):
                # parse the first field too
                inline_match = re.match(r"^-(\s+)([A-Za-z_][A-Za-z0-9_]*):", line)
                if inline_match:
                    cur["existing_fields"].add(inline_match.group(2))
        elif cur is not None:
            m = ID_RE.match(line)
            if m and cur["id"] is None:
                cur["indent"] = m.group(1)
                cur["id"] = m.group(2)
                cur["id_idx"] = i
            else:
                fm = field_re.match(line)
                if fm:
                    cur["existing_fields"].add(fm.group(2))
        i += 1
    if cur is not None:
        cur["end_idx"] = n
        entries.append(cur)

    # Build the output with inserts after each id_idx
    inserts_at = {}  # line index -> list of new lines
    applied = 0
    skipped_existing = 0
    not_in_review = 0
    for ent in entries:
        if ent["id_idx"] is None:
            continue
        pid = ent["id"]
        rec = review.get(pid)
        if rec is None:
            not_in_review += 1
            continue
        new_lines = []
        for field in ("doi", "anthology_id"):
            val = rec.get(field)
            if field in ent["existing_fields"] and not args.overwrite:
                skipped_existing += 1
                continue
            new_lines.append(f"{ent['indent']}{field}: {yaml_value(val)}\n")
        if new_lines:
            inserts_at[ent["id_idx"] + 1] = new_lines
            applied += 1
            if args.limit and applied >= args.limit:
                break

    # Emit
    new_lines_out = []
    for idx, line in enumerate(lines):
        new_lines_out.append(line)
        if idx + 1 in inserts_at:
            new_lines_out.extend(inserts_at[idx + 1])

    summary = (
        f"Entries scanned:       {len(entries)}\n"
        f"Entries not in review: {not_in_review}\n"
        f"Inserts applied:       {applied} entries\n"
        f"Existing fields kept:  {skipped_existing}\n"
        f"Mode:                  {'APPLY' if args.apply else 'DRY RUN'}\n"
    )
    print(summary)

    if args.apply:
        with open(PUB_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines_out)
        print(f"Wrote {PUB_PATH}")
    else:
        # show a small diff sample
        print("\nSample of inserts (first 6):")
        shown = 0
        for idx in sorted(inserts_at.keys()):
            print(f"  after line {idx}:")
            for nl in inserts_at[idx]:
                print(f"    +{nl}", end="")
            shown += 1
            if shown >= 6:
                break


if __name__ == "__main__":
    main()
