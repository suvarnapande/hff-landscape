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

print(f"map: {sum(1 for c in countries if c.get('pop') and c['studies'])} countries with a rate; "
      f"{sum(c['studies'] for c in countries):,} study-country pairs")
print(f"aid vs research: {research_total:,} study-country pairs; DAH 2022-24 mean total {aid_total:,.0f}")
