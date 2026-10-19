"""Data for the two manuscript figures redrawn in theme_hee style (make_figures.R).

Writes, next to this script:
  map_per10m.csv       - studies per 10 million people, by country (fig 1)
  aid_vs_research.csv  - share of DAH vs share of study-country pairs, by GBD super-region (fig 8)

Reads the site data (docs/data, HFF dataset v2.5.1) and the IHME DAH workbook. The region
grouping is copied from build_figures_v2_5.py (fig_aid_vs_evidence_region) so the numbers
match the site figure.
"""
import csv
import json
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
countries = json.loads((DOCS / "data" / "countries.json").read_text(encoding="utf-8"))
geo = json.loads((DOCS / "data" / "geo.json").read_text(encoding="utf-8"))

# ---- fig 1: studies per 10 million people -----------------------------------------
with open(HERE / "map_per10m.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["iso3", "country", "studies", "pop", "per10m"])
    for c in countries:
        rate = 1e7 * c["studies"] / c["pop"] if c.get("pop") and c["studies"] else ""
        w.writerow([c["iso3"], c["country"], c["studies"], c.get("pop") or "", rate])


# ---- fig 8: aid vs research, by GBD super-region -----------------------------------
def gbd_bucket(income, un_region):
    if income == "High income":
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


bucket = [gbd_bucket(c["income"], c["un_region"]) for c in countries]
research = Counter(bucket[c] for c in geo["c"])
research_total = sum(research.values())

f04 = pd.read_excel(DOCS / "dex_hff" / "F04_DAH_by_GBD_super-region_forecast_2015-2030.xlsx", sheet_name="in")
f04 = f04[["Year", "Super-region", "Development assistance for health (DAH) received"]].dropna()
aid = f04[f04["Year"].isin([2022, 2023, 2024])].groupby("Super-region")[
    "Development assistance for health (DAH) received"].mean()
aid_total = aid.sum()

with open(HERE / "aid_vs_research.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["region", "aid_share", "research_share", "research_pairs"])
    for r in sorted(set(aid.index) | set(research), key=lambda b: -aid.get(b, 0)):
        w.writerow([r, 100 * aid.get(r, 0) / aid_total, 100 * research.get(r, 0) / research_total,
                    research.get(r, 0)])

# ---- (Un)equal weight map: financing function tagged most often, by country ----------
# Same rule as build_glance_regions_functions_v2_5.py: Other/Unclear left out; fewer than
# MIN_FN_STUDIES function-tagged studies, or a tie for the lead, has no leading function.
MIN_FN_STUDIES = 5
dct = json.loads((DOCS / "data" / "dict.json").read_text(encoding="utf-8"))
fn_j = json.loads((DOCS / "data" / "function.json").read_text(encoding="utf-8"))
groups = dct["financing_function_grps"]
named = {g for g in groups if g not in ("Other", "Unclear")}
s_fns = {}
for s, g in zip(fn_j["s"], fn_j["g"]):
    if groups[g] in named:
        s_fns.setdefault(s, set()).add(groups[g])
c_studies = {}
for s, c in zip(geo["s"], geo["c"]):
    c_studies.setdefault(c, set()).add(s)
with open(HERE / "leading_function.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["iso3", "country", "studies", "fn_tagged", "status", "leading_function"])
    for i, c in enumerate(countries):
        tagged = [s for s in c_studies.get(i, ()) if s in s_fns]
        cnt = Counter(fn for s in tagged for fn in s_fns[s]).most_common()
        lead = [fn for fn, k in cnt if k == cnt[0][1]] if cnt else []
        status = ("none" if not c["studies"] else "few" if len(tagged) < MIN_FN_STUDIES
                  else "tie" if len(lead) > 1 else "lead")
        w.writerow([c["iso3"], c["country"], c["studies"], len(tagged), status,
                    lead[0] if status == "lead" else ""])

# ---- (Un)equal weight, region profiles (same rules as the web page's cards) ---------
studies = json.loads((DOCS / "data" / "studies.json").read_text(encoding="utf-8"))
out_j = json.loads((DOCS / "data" / "outcome.json").read_text(encoding="utf-8"))
out_groups = dct["outcome_domain_grps"]
fp_studies = {s for s, g in zip(out_j["s"], out_j["g"]) if out_groups[g] == "Financial protection"}
N = len(studies["id"])
REGIONS = ["African Region", "Region of the Americas", "South-East Asia Region", "European Region",
           "Eastern Mediterranean Region", "Western Pacific Region"]
region_of = [c["who_region"] for c in countries]
region_studies = {r: set() for r in REGIONS}
for s, c in zip(geo["s"], geo["c"]):
    region_studies[region_of[c]].add(s)

with open(HERE / "region_functions.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["region", "n_studies", "n_fn_tagged", "function", "share"])
    for r in REGIONS:
        tagged = [s for s in region_studies[r] if s in s_fns]
        cnt = Counter(fn for s in tagged for fn in s_fns[s])
        for fn in sorted(named):
            w.writerow([r, len(region_studies[r]), len(tagged), fn, 100 * cnt[fn] / len(tagged)])

with open(HERE / "region_fp.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["region", "n_studies", "fp_share", "all_studies_fp_share", "all_studies_n"])
    for r in REGIONS:
        ss = region_studies[r]
        w.writerow([r, len(ss), 100 * len(ss & fp_studies) / len(ss), 100 * len(fp_studies) / N, N])

# Cumulative share of a region's countries named by >=1 and >=2 studies, by year
# (2026 is a partial year and is left out, as on the web page).
LAST_FULL_YEAR = 2025
year0 = min(studies["year"])
years_by_c = {}
for s, c in set(zip(geo["s"], geo["c"])):
    years_by_c.setdefault(c, []).append(studies["year"][s])


def coverage(idx):
    first = {c: sorted(years_by_c[c])[0] for c in idx if c in years_by_c}
    second = {c: sorted(years_by_c[c])[1] for c in idx if len(years_by_c.get(c, [])) >= 2}
    for y in range(year0, LAST_FULL_YEAR + 1):
        yield (y, 100 * sum(v <= y for v in first.values()) / len(idx),
               100 * sum(v <= y for v in second.values()) / len(idx))


with open(HERE / "region_trend.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["region", "year", "at_least_one", "two_or_more"])
    for r in REGIONS + ["All regions"]:
        idx = [i for i, c in enumerate(countries) if r == "All regions" or region_of[i] == r]
        for y, one, two in coverage(idx):
            w.writerow([r, y, one, two])

print(f"map: {sum(1 for c in countries if c.get('pop') and c['studies'])} countries with a rate; "
      f"{sum(c['studies'] for c in countries):,} study-country pairs")
print(f"aid vs research: {research_total:,} study-country pairs; DAH 2022-24 mean total {aid_total:,.0f}")
