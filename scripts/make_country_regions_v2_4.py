"""Region reference for the site's countries: WHO region (used on the map), with the UN M49
sub-region (the site's earlier classification, archived) and the World Bank region alongside.
Writes country_regions_v2_4.csv, which build_data_v2_4.py reads into countries.json, and the same
table as country_regions_v2_4.json (with a header saying where it comes from), for sharing.

Sources (fetched online; free, no key):
  who_region  WHO Global Health Observatory, country dimension (ghoapi.azureedge.net), which
              follows WHO's current regional membership (for example Indonesia in the Western
              Pacific since 2025).
  wb_region   World Bank country API (api.worldbank.org/v2/country), region of each economy.
  un_region   unchanged from countries.json (UN M49 sub-region, inherited from the HEE dashboard).

Places with no WHO region (Taiwan is not in the WHO list; Kosovo and Hong Kong are listed without a region)
get the WHO region of the other countries in their UN M49 sub-region, and who_region_source says
so. Taiwan has no World Bank API entry either; it gets East Asia & Pacific, as the World Bank
classifies "Taiwan, China".

Run: python scripts/make_country_regions_v2_4.py   (then build_data_v2_5.py)
"""
import csv
import datetime
import json
import urllib.request
from collections import Counter
from pathlib import Path

DEX = Path(__file__).resolve().parent.parent / "docs" / "dex_hff"
DATA = DEX.parent / "data"
OUT = DEX / "country_regions_v2_4.csv"
OUT_JSON = DEX / "country_regions_v2_4.json"
WHO_URL = "https://ghoapi.azureedge.net/api/DIMENSION/COUNTRY/DimensionValues"
WB_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"

WHO_NAME = {"AFR": "African Region", "AMR": "Region of the Americas", "SEAR": "South-East Asia Region",
            "EUR": "European Region", "EMR": "Eastern Mediterranean Region", "WPR": "Western Pacific Region"}
WB_FALLBACK = {"TWN": "East Asia & Pacific"}  # "Taiwan, China" in World Bank classifications
UA = {"User-Agent": "Mozilla/5.0 (hff-landscape region reference)"}


def fetch_json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())


who = {r["Code"]: WHO_NAME[r["ParentCode"]]
       for r in fetch_json(WHO_URL)["value"]
       if r.get("ParentCode") in WHO_NAME}
wb_rows = fetch_json(WB_URL)[1]
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
OUT_JSON.write_text(json.dumps({
    "description": "WHO region of each country and area in the HFF evidence map, with the earlier UN M49 "
                   "sub-region (archived) and the World Bank region.",
    "fetched": datetime.date.today().isoformat(),
    "sources": {"who_region": WHO_URL, "wb_region": WB_URL,
                "un_region": "UN M49 sub-regions, from the map's country reference (inherited from the HEE dashboard)"},
    "rule": "who_region is the region in the WHO Global Health Observatory's country list. Places that list does "
            "not assign to a region (Taiwan, Hong Kong, Kosovo) get the WHO region of the other countries in "
            "their UN M49 sub-region; who_region_source records this. Membership is a separate question: the "
            "United States and Argentina left the WHO in 2026 but the list keeps them in the Region of the Americas.",
    "n_countries": len(rows),
    "countries": rows,
}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Wrote {OUT} and {OUT_JSON.name} ({len(rows)} countries)")
print("WHO regions:", dict(Counter(r["who_region"] for r in rows)))
for r in rows:
    if r["who_region_source"] != "WHO" or not r["wb_region"]:
        print("  ", r)
