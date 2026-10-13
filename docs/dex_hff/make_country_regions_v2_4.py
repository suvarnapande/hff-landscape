"""Region reference for the site's countries: WHO region (used on the map), with the UN M49
sub-region (the site's earlier classification, archived) and the World Bank region alongside.
Writes country_regions_v2_4.csv, which build_data_v2_4.py reads into countries.json.

Sources (fetched online; free, no key):
  who_region  WHO Global Health Observatory, country dimension (ghoapi.azureedge.net), which
              follows WHO's current regional membership (for example Indonesia in the Western
              Pacific since 2025).
  wb_region   World Bank country API (api.worldbank.org/v2/country), region of each economy.
  un_region   unchanged from countries.json (UN M49 sub-region, inherited from the HEE dashboard).

Places with no WHO region (not WHO members, or listed without a region: Taiwan, Kosovo, Hong Kong)
get the WHO region of the other countries in their UN M49 sub-region, and who_region_source says
so. Taiwan has no World Bank API entry either; it gets East Asia & Pacific, as the World Bank
classifies "Taiwan, China".

Run: python docs/dex_hff/make_country_regions_v2_4.py   (then build_data_v2_4.py)
"""
import csv
import json
import urllib.request
from collections import Counter
from pathlib import Path

DEX = Path(__file__).resolve().parent
DATA = DEX.parent / "data"
OUT = DEX / "country_regions_v2_4.csv"

WHO_NAME = {"AFR": "African Region", "AMR": "Region of the Americas", "SEAR": "South-East Asia Region",
            "EUR": "European Region", "EMR": "Eastern Mediterranean Region", "WPR": "Western Pacific Region"}
WB_FALLBACK = {"TWN": "East Asia & Pacific"}  # "Taiwan, China" in World Bank classifications
UA = {"User-Agent": "Mozilla/5.0 (hff-landscape region reference)"}


def fetch_json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())


who = {r["Code"]: WHO_NAME[r["ParentCode"]]
       for r in fetch_json("https://ghoapi.azureedge.net/api/DIMENSION/COUNTRY/DimensionValues")["value"]
       if r.get("ParentCode") in WHO_NAME}
wb_rows = fetch_json("https://api.worldbank.org/v2/country?format=json&per_page=400")[1]
wb = {r["id"]: r["region"]["value"].strip() for r in wb_rows if r["region"]["value"].strip() != "Aggregates"}

countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
# WHO region most common among the WHO-listed countries of each UN M49 sub-region
by_m49 = {}
for c in countries:
    if c["iso3"] in who and c.get("un_region"):
        by_m49.setdefault(c["un_region"], Counter())[who[c["iso3"]]] += 1

rows = []
for c in countries:
    iso3, m49 = c["iso3"], c.get("un_region")
    if iso3 in who:
        region, source = who[iso3], "WHO"
    elif m49 in by_m49:
        region = by_m49[m49].most_common(1)[0][0]
        source = f"no WHO region; WHO region of its UN M49 sub-region ({m49})"
    else:
        region, source = "", "no WHO region and no UN M49 sub-region"
    rows.append({"iso3": iso3, "country": c["country"], "who_region": region, "who_region_source": source,
                 "un_region": m49 or "", "wb_region": wb.get(iso3, WB_FALLBACK.get(iso3, ""))})

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"Wrote {OUT} ({len(rows)} countries)")
print("WHO regions:", dict(Counter(r["who_region"] for r in rows)))
for r in rows:
    if r["who_region_source"] != "WHO" or not r["wb_region"]:
        print("  ", r)
