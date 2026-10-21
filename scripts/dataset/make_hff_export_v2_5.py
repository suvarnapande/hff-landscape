#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_hff_export_v2_5.py -- assemble the internal team export of the HFF v2.5 dataset.

    python -X utf8 projects/hff/final_includes/make_hff_export_v2_5.py

v2.5 copy (2026-10-13) of make_hff_export_v2_4.py: same logic and checks, pointed at the v2.5 files.
It writes ONLY new v2.5-named files, so every v2.1-v2.4 file in hff_export/ is left as it is.

Writes into `projects/hff/hff_export/`:
  hff_analysis_dataset_v2_5_included.csv   the 53,414 included studies, all 122 analysis columns
  hff_v2_5_all_records.csv                 all 70,230 v2.5 records (80 columns) with exclusion_reason_v2
  column_coverage_v2_5.csv                 per analysis column: type, % present all / included, distinct
  PRISMA_v2_5.json                         the selection flow, copied
  HFF_DATA_DICTIONARY_v2_5.md, V2_5_DATASET_README.md   copied under their own names
  HFF_METHODS_v2_5.md, HFF_METHODS_PUBLICATION_v2_5.md  copies of the current (v2.5-updated) docs
  hff_topic_coordinates_v2_5.csv           per-study topic-map coordinates for all 53,414 v2.5 studies
                                           (53,365 fitted + 49 placed by nearest neighbours, column
                                           topic_placement), copied from make_hff_topic_coordinates_v2_5.py
Two v2.4 files belong to the v2.5 export unchanged and are NOT rewritten (they are v2.4 outputs);
the script only checks that they are already in hff_export/ (make_hff_export_v2_4.py puts them there):
  dedupe_doi_review_v2_4.csv               the DOI de-duplication review (Decision 16)
  hff_topic_coordinates_v2_4.csv           SUPERSEDED by the v2.5 file (the 53,365 fitted studies only);
                                           kept as history

`hff_export/README_v2_5.md` is hand-written and tracked; this script never writes it. It READS it and
FAILS if the row count it states for a CSV is not the count actually written, so the README cannot
drift from the files. It also fails if any column looks like GBD/IHME data, because the README states
that the export contains none.

For the team and co-authors only, not a public release (see the README). Local only: no API calls.
The data and doc copies are regenerable; the script only overwrites files in hff_export/ that it
writes itself (all v2.5-named).
"""
from __future__ import annotations

import csv
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
HFF = HERE.parent
EXP = HFF / "hff_export"
sys.path.insert(0, str(HERE))
import make_hff_codebook_v2_5 as CB  # noqa: E402  (coverage definition shared with the dictionary)

ANALYSIS = HERE / "hff_analysis_dataset_v2_5.parquet"
RECORDS = HERE / "hff_includes_final_v2_5.parquet"
EXPECTED_ROWS, EXPECTED_INCLUDED = CB.EXPECTED_ROWS, CB.EXPECTED_INCLUDED
# source -> name in hff_export/. The two cumulative documents get a _v2_5 suffix so the earlier
# copies already in hff_export/ are not overwritten.
DOCS = {
    HERE / "HFF_DATA_DICTIONARY_v2_5.md": "HFF_DATA_DICTIONARY_v2_5.md",
    HFF / "V2_5_DATASET_README.md": "V2_5_DATASET_README.md",
    HFF / "HFF_METHODS.md": "HFF_METHODS_v2_5.md",
    HFF / "HFF_METHODS_PUBLICATION.md": "HFF_METHODS_PUBLICATION_v2_5.md",
    HERE / "PRISMA_v2_5.json": "PRISMA_v2_5.json",
    # all 53,414 included studies (make_hff_topic_coordinates_v2_5.py); run that script first
    HERE / "hff_topic_coordinates_v2_5.csv": "hff_topic_coordinates_v2_5.csv",
}
# v2.4 files that are part of the v2.5 export unchanged: checked, listed in the README, not rewritten.
REUSED_V2_4 = ["dedupe_doi_review_v2_4.csv", "hff_topic_coordinates_v2_4.csv"]
GBD_PATTERN = re.compile(r"daly|gbd|ihme|burden_of_disease", re.I)


def flatten(df: pd.DataFrame) -> pd.DataFrame:
    """Arrays (func_list) -> '; '-joined strings, so the CSV has one scalar per cell."""
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object and out[c].map(lambda v: isinstance(v, (list, tuple, np.ndarray))).any():
            out[c] = out[c].map(lambda v: "; ".join(map(str, v)) if isinstance(v, (list, tuple, np.ndarray)) else v)
    return out


def count_rows(p: Path) -> int:
    with p.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def main() -> int:
    missing = [str(p) for p in [ANALYSIS, RECORDS, *DOCS] if not p.exists()]
    if missing:
        print("missing inputs:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1
    readme = EXP / "README_v2_5.md"
    if not readme.exists():
        print(f"{readme} not found: the hand-written README must exist first", file=sys.stderr)
        return 1

    a = pd.read_parquet(ANALYSIS)
    r = pd.read_parquet(RECORDS)
    gbd = [c for c in list(a.columns) + list(r.columns) if GBD_PATTERN.search(c)]
    if gbd:
        print(f"GBD/IHME-like columns found {gbd}: update the README licensing note first", file=sys.stderr)
        return 1
    inc = a["analysis_include"].astype(bool)
    assert inc.sum() == r["analysis_include"].astype(bool).sum() == EXPECTED_INCLUDED
    assert a["record_id"].is_unique and r["record_id"].is_unique and len(a) == len(r) == EXPECTED_ROWS

    EXP.mkdir(exist_ok=True)
    written = {}
    p = EXP / "hff_analysis_dataset_v2_5_included.csv"
    flatten(a[inc]).to_csv(p, index=False, encoding="utf-8")
    written[p.name] = int(inc.sum())
    p = EXP / "hff_v2_5_all_records.csv"
    flatten(r).to_csv(p, index=False, encoding="utf-8")
    written[p.name] = len(r)
    p = EXP / "column_coverage_v2_5.csv"
    CB.coverage(a, inc).to_csv(p, index=False, encoding="utf-8")
    written[p.name] = a.shape[1]
    for src, name in DOCS.items():
        shutil.copy2(src, EXP / name)
    # the coordinates file must have one row per included study (checked like the CSVs above)
    written["hff_topic_coordinates_v2_5.csv"] = int(inc.sum())

    # verify: rows on disk == rows intended == rows the README states
    text = readme.read_text(encoding="utf-8")
    errs = []
    for name, n in written.items():
        on_disk = count_rows(EXP / name)
        if on_disk != n:
            errs.append(f"{name}: wrote {n:,} rows but {on_disk:,} read back")
        line = next((ln for ln in text.splitlines() if ln.startswith(f"| `{name}`")), None)
        if line is None:
            errs.append(f"{name}: no row in the README files table")
        elif f"{on_disk:,}" not in line:
            errs.append(f"{name}: README states a different row count (file has {on_disk:,}): {line[:120]}")
    if f"{EXPECTED_INCLUDED:,}" not in text:
        errs.append(f"README does not state the {EXPECTED_INCLUDED:,} included studies")
    for name in DOCS.values():
        if not any(ln.startswith(f"| `{name}`") for ln in text.splitlines()):
            errs.append(f"{name}: copied but not listed in the README files table")
    for name in REUSED_V2_4:
        if not (EXP / name).exists():
            errs.append(f"{name}: not in hff_export/ (run make_hff_export_v2_4.py first)")
        if not any(ln.startswith(f"| `{name}`") for ln in text.splitlines()):
            errs.append(f"{name}: part of the v2.5 export but not listed in the README files table")

    print(f"analysis rows {len(a):,}, included {int(inc.sum()):,}, columns {a.shape[1]}; "
          f"record table {len(r):,} x {r.shape[1]}\n")
    print(f"files in {EXP} (data rows, excluding the header):")
    for f in sorted(EXP.iterdir()):
        n = f"{count_rows(f):,}" if f.suffix == ".csv" else "-"
        print(f"  {f.name:45s} {n:>10s} rows  {f.stat().st_size / 1024:12,.1f} KB")
    if errs:
        print("\nREADME CHECK FAILED:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    print("\nREADME_v2_5.md row counts verified against the files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
