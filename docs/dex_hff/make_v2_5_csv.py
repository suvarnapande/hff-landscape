"""HFF dataset v2.5.1 -> v2_5_1/hff_v2_5_1_site.csv, laid out like the v5 extraction CSV so the
*_v2_5.py build scripts can read it the way the v5 scripts read hsf_extraction_29sept_v5.csv.
v2.5 copy of make_v2_4_csv.py (itself a copy of make_v2_2_csv.py); the recoding below is unchanged.

Input:  v2_5_1/hff_analysis_dataset_v2_5_1_included.csv (53,411 included studies; every row is
        an included study, so nothing is filtered on inclusion). v2.5.1 is the dataset team's
        v2.5 (v2.4 plus Decision 17: self-described HTAs are Benefits decisions; also_in_hee flag)
        without three studies published before 2010 (make_v2_5_1.py, v2_5_1/CHANGES_v2_5_1.md).

What changes from the v2.2 file:
  - financing_function_final = financing_function_v52 (the v52 label; v5 used the v41 label)
  - income_level is recoded to the v5 codes the scripts expect (HIC / MIC = upper middle /
    LMIC / LIC). It stays the CURRENT (FY2027) World Bank group, the v2.2 default.
  - has_error = 0 for every row (v2.2 only keeps it for v1 rows; every included study was
    extracted)
  - nothing is left out: the build stops if any study falls outside 2010-2026. The three
    pre-2010 studies (no year at EPPI import, December 2009 articles) are excluded upstream,
    in v2.5.1; see DATA_GAPS_v2_5.md, item 5
  - function_label_source is kept, for the with/without second-opinion sensitivity figure

The bibliographic, topic and MeSH columns are copied as they are; in v2.5 they are filled for
the studies added after v1 too, except the topic columns of the 49 HTA studies Decision 17
re-included (not in the topic model).

Run: python docs/dex_hff/make_v2_5_csv.py
"""
from pathlib import Path

import pandas as pd

DEX = Path(__file__).resolve().parent
src = DEX / "v2_5_1" / "hff_analysis_dataset_v2_5_1_included.csv"
dst = DEX / "v2_5_1" / "hff_v2_5_1_site.csv"

INCOME_CODE = {
    "High income": "HIC",
    "Upper middle income": "MIC",
    "Lower middle income": "LMIC",
    "Low income": "LIC",
}

df = pd.read_csv(src, dtype=str, keep_default_na=False, na_values=[""])
n_in = len(df)

# The publication-year criterion is 2010 onwards. v2.2.1 already excludes the three pre-2010
# studies (make_v2_2_1.py); stop if any other study falls outside the window.
years = pd.to_numeric(df["year"], errors="coerce")
outside_window = ~years.between(2010, 2026)
assert not outside_window.any(), (
    "studies outside 2010-2026 or without a year: "
    f"{', '.join(df.loc[outside_window, 'record_id'])}; exclude them upstream (see make_v2_5_1.py)")

df["financing_function_final"] = df["financing_function_v52"]


def recode_income(v):
    if pd.isna(v):
        return v
    codes = [INCOME_CODE.get(t.strip()) for t in str(v).split(";") if t.strip()]
    unknown = [t for t, c in zip(str(v).split(";"), codes) if c is None]
    if unknown:
        raise ValueError(f"unrecognised income group(s) {unknown!r} in {v!r}")
    return "; ".join(codes)


df["income_level"] = df["income_level"].map(recode_income)
df["has_error"] = "0"

df.to_csv(dst, index=False, encoding="utf-8")
print(f"{n_in:,} included studies in -> {len(df):,} rows out: {dst}")
print("Income groups:", df["income_level"].value_counts(dropna=False).head(6).to_dict())
print("Function label source:", df["function_label_source"].value_counts().to_dict())
