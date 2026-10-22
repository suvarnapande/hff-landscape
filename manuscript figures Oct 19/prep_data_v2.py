"""v2 of prep_data.py (22 October 2026): the inputs that depend on income group, recomputed so that
studies are counted by the World Bank income group of each country studied IN THE STUDY'S
PUBLICATION YEAR (docs/data/geo.json "i", per study-country pair), not the current FY2027 group.
prep_data.py and the CSVs it writes are kept; this script writes only new _v2 files:

  kpis_v2.csv                         kpis.csv with lmic_pct on the publication-year basis
  aid_vs_research_v2.csv              fig 8; Mauritius and Eritrea (no UN sub-region) now count in
                                      Sub-Saharan Africa instead of falling through to High-income.
                                      GBD super-regions stay approximated by the CURRENT (FY2027) group:
                                      they are a fixed country grouping, not a count by income
  oa_by_income_v2.csv                 per study with a DOI: record_id, is_oa, income group of the
                                      countries studied (publication year) for the open-access figure
  fig2_functions_by_income_v2.csv     manuscript Figure 2: share of single-country studies addressing
                                      each function, high income vs low and middle income
  fig7_author_location_by_income_v2.csv  manuscript Figure 7: where the authors of single-country
                                      studies are based, by income group

Run from this folder, after prep_data.py:  python prep_data_v2.py
"""
import ast
import csv
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DOCS = ROOT / "docs"
D = DOCS / "data"
countries = json.loads((D / "countries.json").read_text(encoding="utf-8"))
geo = json.loads((D / "geo.json").read_text(encoding="utf-8"))
dct = json.loads((D / "dict.json").read_text(encoding="utf-8"))
studies = json.loads((D / "studies.json").read_text(encoding="utf-8"))
fn_j = json.loads((D / "function.json").read_text(encoding="utf-8"))
INC_LV = dct["levels"]["income"]
HI = "High income"

# publication-year income group per (study, country) pair
pair_inc = {(s, c): (INC_LV[i] if i >= 0 else None) for s, c, i in zip(geo["s"], geo["c"], geo["i"])}
s_cs = {}
for s, c in zip(geo["s"], geo["c"]):
    s_cs.setdefault(s, set()).add(c)


def groups_of(s):
    return {pair_inc[(s, c)] for c in s_cs.get(s, ())} - {None}


# ---- kpis_v2.csv: lmic_pct by publication-year group -------------------------------
with open(HERE / "kpis.csv", encoding="utf-8") as f:
    kpis = dict(csv.reader(f))
kpis.pop("key", None)
with_inc = [s for s in s_cs if groups_of(s)]
kpis["lmic_pct"] = 100 * sum(bool(groups_of(s) - {HI}) for s in with_inc) / len(with_inc)
with open(HERE / "kpis_v2.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["key", "value"])
    w.writerows(kpis.items())


# ---- aid_vs_research_v2.csv: fig 8 -------------------------------------------------
def gbd_bucket(income, un_region):
    if income == HI:
        return "High-income"
    return {
        "Sub-Saharan Africa": "Sub-Saharan Africa",
        "Southern Asia": "South Asia",
        "Eastern Asia": "Southeast Asia, East Asia, and Oceania",
        "South-eastern Asia": "Southeast Asia, East Asia, and Oceania",
        "Melanesia": "Southeast Asia, East Asia, and Oceania",
        "Micronesia": "Southeast Asia, East Asia, and Oceania",
        "Polynesia": "Southeast Asia, East Asia, and Oceania",
        "Northern Africa": "North Africa and Middle East",
        "Western Asia": "North Africa and Middle East",
        "Latin America and the Caribbean": "Latin America and Caribbean",
        "Eastern Europe": "Central Europe, Eastern Europe, and Central Asia",
        "Central Asia": "Central Europe, Eastern Europe, and Central Asia",
        "Southern Europe": "Central Europe, Eastern Europe, and Central Asia",
    }.get(un_region, "High-income")


# Mauritius and Eritrea have no un_region in countries.json; both are Sub-Saharan Africa in GBD.
bucket = [gbd_bucket(c["income"], c["un_region"] or ("Sub-Saharan Africa" if c["who_region"] == "African Region"
                                                     else None)) for c in countries]
research = Counter(bucket[c] for c in geo["c"])
research_total = sum(research.values())
f04 = pd.read_excel(DOCS / "dex_hff" / "F04_DAH_by_GBD_super-region_forecast_2015-2030.xlsx", sheet_name="in")
f04 = f04[["Year", "Super-region", "Development assistance for health (DAH) received"]].dropna()
aid = f04[f04["Year"].isin([2022, 2023, 2024])].groupby("Super-region")[
    "Development assistance for health (DAH) received"].mean()
aid_total = aid.sum()
with open(HERE / "aid_vs_research_v2.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["region", "aid_share", "research_share", "research_pairs"])
    for r in sorted(set(aid.index) | set(research), key=lambda b: -aid.get(b, 0)):
        w.writerow([r, 100 * aid.get(r, 0) / aid_total, 100 * research.get(r, 0) / research_total,
                    research.get(r, 0)])

# ---- oa_by_income_v2.csv: open access by income group of the countries studied -----
raw = pd.read_csv(DOCS / "dex_hff" / "v2_5_1" / "hff_v2_5_1_site.csv", low_memory=False, dtype=str,
                  usecols=["record_id", "doi", "is_oa", "author_affiliation_countries"]).set_index("record_id")
ids = studies["id"]


def oa_group(s):
    g = groups_of(s)
    if not g:
        return "No income group"
    if g == {HI}:
        return "High income"
    return "Low and middle income" if HI not in g else "Both"


with open(HERE / "oa_by_income_v2.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["record_id", "is_oa", "group"])
    for s, rid in enumerate(ids):
        r = raw.loc[str(rid)]
        if isinstance(r["doi"], str) and r["doi"].strip():
            w.writerow([rid, r["is_oa"], oa_group(s)])

# ---- fig2_functions_by_income_v2.csv ------------------------------------------------
fn_groups = dct["financing_function_grps"]
s_fns = {}
for s, g in zip(fn_j["s"], fn_j["g"]):
    s_fns.setdefault(s, set()).add(fn_groups[g])
single = {s: next(iter(cs)) for s, cs in s_cs.items() if len(cs) == 1}
inc_single = {s: pair_inc[(s, c)] for s, c in single.items() if pair_inc[(s, c)]}
grp2 = {"High income": [s for s, g in inc_single.items() if g == HI],
        "Low and middle income": [s for s, g in inc_single.items() if g != HI]}
FN2 = [("Benefits decisions", "Benefits decisions"), ("Purchasing", "Purchasing"), ("Pooling", "Pooling"),
       ("Revenue Raising", "Revenue raising"), ("Public financial management", "Public financial management"),
       ("Overall", "Financing system as a whole"),
       ("Recurrent financing for the procurement and distribution of supply chain inputs", "Supply-chain financing"),
       ("Capital investment: other health system inputs", "Capital investment: other inputs"),
       ("Capital investment: infrastructure", "Capital investment: infrastructure")]
for code, _ in FN2:
    assert code in fn_groups, code
with open(HERE / "fig2_functions_by_income_v2.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["group", "n", "function", "share"])
    for g, ss in grp2.items():
        for code, label in FN2:
            w.writerow([g, len(ss), label, 100 * sum(code in s_fns.get(s, ()) for s in ss) / len(ss)])

# ---- fig7_author_location_by_income_v2.csv -----------------------------------------
src = (ROOT / "scripts" / "build_figures_v2_5.py").read_text(encoding="utf-8")
ISO2_TO_ISO3 = ast.literal_eval(re.search(r"ISO2_TO_ISO3 = (\{.*?\n\})", src, re.S).group(1))


def author_iso3(v):
    if not isinstance(v, str) or v.strip() in ("", "Could not find"):
        return set()
    return {ISO2_TO_ISO3[t.strip()] for t in re.split(r"[;,]", v) if t.strip() in ISO2_TO_ISO3}


iso3 = [c["iso3"] for c in countries]
loc = {g: Counter() for g in INC_LV}
for s, g in inc_single.items():
    ac = author_iso3(raw.loc[str(ids[s]), "author_affiliation_countries"])
    if not ac:
        continue
    home = iso3[single[s]]
    loc[g]["Authors based only in the country studied" if ac == {home} else
           "Authors based in and outside the country" if home in ac else "No author based in the country"] += 1
with open(HERE / "fig7_author_location_by_income_v2.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["income", "n", "location", "studies", "share"])
    for g in INC_LV:
        n = sum(loc[g].values())
        for k in ("Authors based only in the country studied", "Authors based in and outside the country",
                  "No author based in the country"):
            w.writerow([g, n, k, loc[g][k], 100 * loc[g][k] / n])

print(f"lmic_pct (publication year): {kpis['lmic_pct']:.1f}%")
print(f"fig 2 bases: high income {len(grp2['High income']):,}, L&MIC {len(grp2['Low and middle income']):,}")
print(f"fig 7 base: {sum(sum(v.values()) for v in loc.values()):,} single-country studies with an author country")
print(f"fig 8: Sub-Saharan Africa {100 * research['Sub-Saharan Africa'] / research_total:.1f}% of {research_total:,} pairs")
