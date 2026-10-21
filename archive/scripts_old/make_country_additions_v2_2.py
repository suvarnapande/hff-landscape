"""Reference rows for the 31 countries that v2.2 studies name but the site's country list
(docs/data/countries.json, inherited from the HEE dashboard) did not have. Writes
country_additions_v2_2.csv, which build_data_v2_2.py appends to the country list.

Sources (fetched online; free, no key):
  pop             UN World Population Prospects 2024, 2025 medium-variant estimate, via Our World
                  in Data (population-with-un-projections). Same source as the existing rows.
  total_spend_bn  World Bank SH.XPD.CHEX.PP.CD (current health expenditure per person, PPP current
                  international $), 2022, x UN 2022 population. The existing rows come from a
                  similar but not identical source (within ~5% of the World Bank series), so these
                  values are close, not strictly comparable. Blank where the World Bank has no value
                  (Taiwan, Puerto Rico, Kosovo, Bermuda, Greenland).
  dalys           Preserves verified IHME GBD 2023 totals already in the output CSV.
                  Thirty additions were filled from the supplied IHME country export;
                  Kosovo remains blank because it is absent from the export.
  income          v2.2 income_level (World Bank FY2027) of the studies naming the country.
  un_region       UN M49 sub-region, as in the existing rows (Kosovo: Southern Europe, like Serbia).

Run: python docs/dex_hff/make_country_additions_v2_2.py   (then build_data_v2_2.py)
"""
import csv
import io
import json
import urllib.request
from collections import Counter
from pathlib import Path

import pandas as pd

DEX = Path(__file__).resolve().parent
OUT = DEX / "country_additions_v2_2.csv"
existing_dalys = {}
if OUT.exists():
    with OUT.open(newline="", encoding="utf-8-sig") as fh:
        existing_dalys = {row["iso3"]: row["dalys"] for row in csv.DictReader(fh)}
SITE_CSV = DEX / "v2_2" / "hff_v2_2_site.csv"

# country name as v2.2's geo_final spells it -> (iso3, UN M49 sub-region, OWID population code)
ADD = {
    "Taiwan": ("TWN", "Eastern Asia", "TWN"),
    "Israel": ("ISR", "Western Asia", "ISR"),
    "Kazakhstan": ("KAZ", "Central Asia", "KAZ"),
    "Cuba": ("CUB", "Latin America and the Caribbean", "CUB"),
    "Palestine": ("PSE", "Western Asia", "PSE"),
    "Bhutan": ("BTN", "Southern Asia", "BTN"),
    "Luxembourg": ("LUX", "Western Europe", "LUX"),
    "Iceland": ("ISL", "Northern Europe", "ISL"),
    "Fiji": ("FJI", "Melanesia", "FJI"),
    "Puerto Rico": ("PRI", "Latin America and the Caribbean", "PRI"),
    "Kosovo": ("XKX", "Southern Europe", "OWID_KOS"),
    "Solomon Islands": ("SLB", "Melanesia", "SLB"),
    "Maldives": ("MDV", "Southern Asia", "MDV"),
    "Guyana": ("GUY", "Latin America and the Caribbean", "GUY"),
    "Barbados": ("BRB", "Latin America and the Caribbean", "BRB"),
    "Tonga": ("TON", "Polynesia", "TON"),
    "Belize": ("BLZ", "Latin America and the Caribbean", "BLZ"),
    "Vanuatu": ("VUT", "Melanesia", "VUT"),
    "Palau": ("PLW", "Micronesia", "PLW"),
    "Montenegro": ("MNE", "Southern Europe", "MNE"),
    "Malta": ("MLT", "Southern Europe", "MLT"),
    "Samoa": ("WSM", "Polynesia", "WSM"),
    "Grenada": ("GRD", "Latin America and the Caribbean", "GRD"),
    "Brunei": ("BRN", "South-eastern Asia", "BRN"),
    "Micronesia": ("FSM", "Micronesia", "FSM"),
    "Bermuda": ("BMU", "Northern America", "BMU"),
    "Greenland": ("GRL", "Northern America", "GRL"),
    "Saint Vincent and the Grenadines": ("VCT", "Latin America and the Caribbean", "VCT"),
    "Kiribati": ("KIR", "Micronesia", "KIR"),
    "Comoros": ("COM", "Sub-Saharan Africa", "COM"),
    "Saint Lucia": ("LCA", "Latin America and the Caribbean", "LCA"),
}
# other v2.2 spellings of the same countries (build_data_v2_2.py reads these too)
ALIASES = {
    "Occupied Palestinian Territory": "Palestine",
    "Brunei Darussalam": "Brunei",
    "Federated States of Micronesia": "Micronesia",
}
INCOME_NAME = {"HIC": "High income", "MIC": "Upper middle income", "LMIC": "Lower middle income", "LIC": "Low income"}
UA = {"User-Agent": "Mozilla/5.0 (hff-landscape country reference build)"}


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read().decode("utf-8")


# population: UN WPP 2025 (medium projection) and 2022 (estimate)
pop25, pop22 = {}, {}
for r in csv.DictReader(io.StringIO(fetch(
        "https://ourworldindata.org/grapher/population-with-un-projections.csv"
        "?v=1&csvType=full&useColumnShortNames=true"))):
    if r["year"] == "2025" and r["population__sex_all__age_all__variant_medium__projected"]:
        pop25[r["code"]] = float(r["population__sex_all__age_all__variant_medium__projected"])
    if r["year"] == "2022" and r["population__sex_all__age_all__variant_estimates"]:
        pop22[r["code"]] = float(r["population__sex_all__age_all__variant_estimates"])

# health spending per person, PPP, 2022 (World Bank)
iso = [v[0] for v in ADD.values()]
wb = json.loads(fetch("https://api.worldbank.org/v2/country/" + ";".join(iso)
                      + "/indicator/SH.XPD.CHEX.PP.CD?format=json&per_page=1000&date=2022"))[1] or []
che = {r["countryiso3code"]: r["value"] for r in wb if r["value"] is not None}

# income group: the v2.2 value for single-country studies naming the country
site = pd.read_csv(SITE_CSV, usecols=["geo_final", "income_level"], dtype=str, low_memory=False)
name_of = {**{n: n for n in ADD}, **ALIASES}
inc = {n: Counter() for n in ADD}
for geo, lvl in zip(site["geo_final"], site["income_level"]):
    if pd.isna(geo) or pd.isna(lvl) or ";" in lvl:
        continue
    toks = [t.strip() for t in geo.split(",") if t.strip()]
    if len(toks) == 1 and toks[0] in name_of:
        inc[name_of[toks[0]]][INCOME_NAME[lvl.strip()]] += 1

rows = []
for name, (iso3, region, pop_code) in ADD.items():
    p25, p22 = pop25.get(pop_code), pop22.get(pop_code)
    spend = che.get(iso3)
    rows.append({
        "iso3": iso3, "country": name,
        "income": inc[name].most_common(1)[0][0] if inc[name] else "",
        "un_region": region,
        "pop": round(p25) if p25 else "",
        "dalys": existing_dalys.get(iso3, ""),
        "total_spend_bn": round(spend * p22 / 1e9, 6) if (spend and p22) else "",
    })
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"Wrote {OUT} ({len(rows)} countries)")
for r in rows:
    print(f"  {r['iso3']} {r['country']:34} {r['income']:22} {r['un_region']:32} pop={r['pop']} spend_bn={r['total_spend_bn']}")
