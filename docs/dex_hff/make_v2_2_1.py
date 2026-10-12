"""HFF dataset v2.2 -> v2.2.1: excludes three studies published before 2010.

v2.2.1 is v2.2 with one change. Three records came from EPPI-Reviewer with no publication year,
so the 2010-onwards criterion could not be applied; they were screened, labelled and included.
An online check (CrossRef and OpenAlex, 2026-10-12) found no version published in 2010 or later:
all three are articles in Inquiry 46(4), "Winter 2009/2010", published December 2009. They are
excluded under the publication-year criterion as `published_before_2010`, the last exclusion
test (applied after de-duplication). See CHANGES_v2_2_1.md and DATA_GAPS_v2_2.md, item 5.

The v2.2 files are left unchanged. Writes, in docs/dex_hff/v2_2/:
  hff_analysis_dataset_v2_2_1_included.csv   53,779 included studies
  hff_v2_2_1_all_records.csv                 70,230 records; the three now analysis_include False
  PRISMA_v2_2_1.json                         selection flow with the new exclusion line
  CHANGES_v2_2_1.md                          what changed and why

Run: python docs/dex_hff/make_v2_2_1.py
"""
import json
from pathlib import Path

import pandas as pd

V22 = Path(__file__).resolve().parent / "v2_2"
REASON = "published_before_2010"
PRE_2010 = {
    "132855712": "Incentives in Obesity and Health Insurance (10.5034/inquiryjrnl_46.4.418)",
    "132855713": "Medicare Savings Programs: Analyzing Options for Expanding Eligibility (10.5034/inquiryjrnl_46.4.391)",
    "132855714": "Medicare Fees and the Volume of Physicians' Services (10.5034/inquiryjrnl_46.4.372)",
}


def read(name):
    # keep every cell exactly as written: no type inference, empty cells stay empty
    return pd.read_csv(V22 / name, dtype=str, keep_default_na=False)


# --- analysis file: drop the three rows -------------------------------------------------
inc = read("hff_analysis_dataset_v2_2_included.csv")
drop = inc["record_id"].isin(PRE_2010)
assert drop.sum() == len(PRE_2010), "not all three records are in the v2.2 analysis file"
origin_of = dict(zip(inc.loc[drop, "record_id"], inc.loc[drop, "origin"]))
inc[~drop].to_csv(V22 / "hff_analysis_dataset_v2_2_1_included.csv", index=False, encoding="utf-8")
print(f"analysis file: {len(inc):,} -> {int((~drop).sum()):,} included studies")

# --- record table: mark them excluded -----------------------------------------------------
rec = read("hff_v2_2_all_records.csv")
hit = rec["record_id"].isin(PRE_2010)
assert hit.sum() == len(PRE_2010), "not all three records are in the v2.2 record table"
assert (rec.loc[hit, "analysis_include"] == "True").all(), "the three are not marked included in v2.2"
rec.loc[hit, "analysis_include"] = "False"
rec.loc[hit, "exclusion_reason_v2"] = REASON
rec.to_csv(V22 / "hff_v2_2_1_all_records.csv", index=False, encoding="utf-8")
print(f"record table: {len(rec):,} records; included {int((rec['analysis_include'] == 'True').sum()):,}")

# --- PRISMA: move the three from INCLUDED to the new exclusion line -------------------------
prisma = json.loads((V22 / "PRISMA_v2_2.json").read_text(encoding="utf-8"))
for rid, route in origin_of.items():
    lines = prisma["routes"][route]["lines"]
    lines["INCLUDED"] -= 1
    lines[REASON] = lines.get(REASON, 0) + 1
    prisma["included_by_route"][route] -= 1
prisma["excluded"][REASON] = len(PRE_2010)
prisma["included"] -= len(PRE_2010)
assert prisma["included"] == sum(prisma["included_by_route"].values())
assert prisma["pool_total"] == prisma["included"] + sum(prisma["excluded"].values())
prisma["version"] = "2.2.1"
prisma["v2_2_1_change"] = (f"{len(PRE_2010)} records excluded as {REASON} "
                           f"({', '.join(sorted(PRE_2010))}): no year at EPPI import; December 2009 "
                           "publications (CrossRef, OpenAlex, checked 2026-10-12). See CHANGES_v2_2_1.md.")
(V22 / "PRISMA_v2_2_1.json").write_text(json.dumps(prisma, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"PRISMA: included {prisma['included']:,}; reconciles")

# --- change note ----------------------------------------------------------------------------
rows = "\n".join(f"| {rid} | {origin_of[rid]} | {PRE_2010[rid]} |" for rid in sorted(PRE_2010))
(V22 / "CHANGES_v2_2_1.md").write_text(f"""# HFF dataset v2.2.1

v2.2.1 is v2.2 with three studies excluded. **Included studies: {prisma['included']:,}** (v2.2: 53,782).
Made by `docs/dex_hff/make_v2_2_1.py` in the hff-landscape repository; the v2.2 files are unchanged.

## What changed

Three records are now excluded with `exclusion_reason_v2 = {REASON}`:

| record_id | route (`origin`) | title (DOI) |
|---|---|---|
{rows}

## Why

The map includes studies published from 2010 onwards. These three records came from the search
results imported into EPPI-Reviewer with no publication year, so the year criterion could not be
applied at screening. They went through screening, labelling and extraction like every other
record and were included in v2.2 (which later gave them the year 2009).

An online check on 2026-10-12 (CrossRef and OpenAlex) found no version published in 2010 or
later. All three are articles in *Inquiry* volume 46, issue 4 ("Winter 2009/2010"), which both
databases date December 2009; the first is also an NBER working paper from May 2007. Their latest
publication year is 2009, so they are excluded under the publication-year criterion. Their DOIs
were registered only in August 2011, which may be why the year was missing at import.

## Files

| v2.2.1 file | change from v2.2 |
|---|---|
| `hff_analysis_dataset_v2_2_1_included.csv` | the three rows removed ({prisma['included']:,} rows) |
| `hff_v2_2_1_all_records.csv` | the three rows: `analysis_include` False, `exclusion_reason_v2` `{REASON}` |
| `PRISMA_v2_2_1.json` | new exclusion line `{REASON}` (applied last, after de-duplication); included and route totals reduced |

Everything else (columns, values, documentation) is as in v2.2.
""", encoding="utf-8")
print("wrote CHANGES_v2_2_1.md")
