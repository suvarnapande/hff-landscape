"""Audit: the numbers behind and on the manuscript figures in this folder.

  1. every CSV that prep_data.py writes (the figures' inputs), recomputed from the raw dataset;
  2. the site's processed files those CSVs were built from (countries.json study counts);
  3. numbers typed into the R scripts by hand (manuscript-text totals), against the data.

Run from this folder, after prep_data.py:  python audit_figures.py
Writes audit_figures_report.md. Statuses: PASS, DIFF, INFO (shown for the record).
Shares are compared to 0.05 percentage points; counts must match exactly.
"""
import csv
import json
import re
from collections import Counter

import pandas as pd

from audit_common import DOCS, HERE, LAST_FULL_YEAR, Data, report

d = Data()
rows = []


def read(name):
    with open(HERE / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check(name, expected, actual, tol=None, note=""):
    if tol is None:
        ok = expected == actual
        e, a = f"{expected:,}" if isinstance(expected, int) else expected, f"{actual:,}" if isinstance(actual, int) else actual
    else:
        ok = abs(float(expected) - float(actual)) <= tol
        e, a = f"{float(expected):.2f}", f"{float(actual):.2f}"
    rows.append({"check": name, "expected": e, "actual": a, "status": "PASS" if ok else "DIFF", "note": note})


def info(name, expected, actual, note):
    rows.append({"check": name, "expected": expected, "actual": actual, "status": "INFO", "note": note})


def all_pass(name, items, note=""):
    """items: (label, expected, actual, tol); one row summarising many comparisons."""
    bad = [(lbl, e, a) for lbl, e, a, tol in items
           if (abs(float(e) - float(a)) > tol if tol is not None else e != a)]
    rows.append({"check": name, "expected": f"{len(items)} values", "actual": f"{len(items) - len(bad)} match",
                 "status": "PASS" if not bad else "DIFF",
                 "note": note if not bad else "; ".join(f"{l}: {e} vs {a}" for l, e, a in bad[:6])})


cstud = d.country_studies()
n_per_country = {c["country"]: len(cstud.get(c["country"], ())) for c in d.countries}

# ---- site data the figure CSVs come from ----------------------------------------------
all_pass("countries.json study counts vs raw", [(c["country"], c["studies"], n_per_country[c["country"]], None)
                                                 for c in d.countries])
site_pairs = sum(c["studies"] for c in d.countries)
check("Study-country pairs: site total vs distinct pairs in raw", site_pairs, d.pairs(),
      note="site geo.json keeps a pair once per matching place name, so a study naming e.g. England and "
           "Scotland counts twice for the United Kingdom")

# ---- figure 1 (studies per 10 million people) ------------------------------------------
m = read("map_per10m.csv")
all_pass("Fig 1 map_per10m.csv: studies per country", [(r["iso3"], int(r["studies"]), n_per_country[r["country"]], None) for r in m])
pop = {c["iso3"]: c.get("pop") for c in d.countries}
all_pass("Fig 1 map_per10m.csv: rate per 10 million", [
    (r["iso3"], float(r["per10m"]), 1e7 * n_per_country[r["country"]] / pop[r["iso3"]], 1e-6)
    for r in m if r["per10m"]])

# ---- glance figure 1: studies per 100,000 DALYs + headline numbers ------------------------
m = read("map_per100k_dalys.csv")
dal = {c["iso3"]: c.get("dalys") for c in d.countries}
all_pass("Glance 1 map_per100k_dalys.csv: rate per 100,000 DALYs", [
    (r["iso3"], float(r["per100k_dalys"]), 1e5 * n_per_country[r["country"]] / dal[r["iso3"]], 1e-6)
    for r in m if r["per100k_dalys"]])
check("Glance 1 caption: countries with a rate", 182, sum(1 for r in m if r["per100k_dalys"]))

K = {r["key"]: r["value"] for r in read("kpis.csv")}
check("Headline: studies", int(K["n_studies"]), d.N)
check("Headline: countries with at least one study (data)", int(K["n_countries_named"]), len(d.countries_named()))
named_studies = [i for i in range(d.N) if d.study_countries[i]]
check("Headline: studies naming a country", int(K["n_country_named_studies"]), len(named_studies))
fp = [i for i in range(d.N) if "Financial protection" in d.outcomes[i]]
base = d.with_outcome()
check("Headline: financial protection, all studies (%)", K["fp_pct"], 100 * len(fp) / d.N, 0.05)
check("Headline: studies with a recorded outcome", int(K["n_with_outcome"]), len(base))
check("Headline: financial protection, studies with a recorded outcome (%)", K["fp_pct_outcome"],
      100 * len(fp) / len(base), 0.05)
tagged = [i for i in range(d.N) if d.named_functions[i]]
top_fn, top_n = Counter(f for i in tagged for f in d.named_functions[i]).most_common(1)[0]
check("Headline: most studied function", K["top_fn"], top_fn)
check("Headline: its share of function-tagged studies (%)", K["top_fn_pct"], 100 * top_n / len(tagged), 0.05)
inc = {c["country"]: c["income"] for c in d.countries}
with_inc = [cs for cs in d.study_countries if any(inc[c] for c in cs)]
check("Headline: focus on low- and middle-income countries (%)", K["lmic_pct"],
      100 * sum(any(inc[c] and inc[c] != "High income" for c in cs) for cs in with_inc) / len(with_inc), 0.05)
has_doi = d.raw["doi"].notna() & (d.raw["doi"].astype(str).str.strip() != "")
oa_raw = 100 * d.raw.loc[has_doi, "is_oa"].astype(str).str.lower().isin(["true", "1", "yes"]).mean()
check("Headline: open access (%) vs raw is_oa among studies with a DOI", K["oa_pct"], oa_raw, 0.5,
      note="headline comes from open_access_v5.json (OpenAlex match); raw is_oa is a second source")

# ---- glance figure 2 / unequal-weight figures: region profiles ---------------------------
reg = d.region_studies()
items = []
for r in read("region_functions.csv"):
    ss = [i for i in reg[r["region"]] if d.named_functions[i]]
    items.append((f"{r['region']} / {r['function']}", float(r["share"]),
                  100 * sum(r["function"] in d.named_functions[i] for i in ss) / len(ss), 0.05))
    items.append((f"{r['region']} n", int(r["n_studies"]), len(reg[r["region"]]), None))
all_pass("Region profiles region_functions.csv: function shares and n", items)

items = []
for r in read("region_fp.csv"):
    ss = reg[r["region"]]
    so = [i for i in ss if d.outcomes[i] - {"Unclear"}]
    items += [(f"{r['region']} all studies", float(r["fp_share"]),
               100 * sum("Financial protection" in d.outcomes[i] for i in ss) / len(ss), 0.05),
              (f"{r['region']} recorded outcome", float(r["fp_share_outcome"]),
               100 * sum("Financial protection" in d.outcomes[i] for i in so) / len(so), 0.05)]
all_pass("Region profiles region_fp.csv: financial protection shares (both bases)", items)

years_by_c = {}
for i, cs in enumerate(d.study_countries):
    for c in cs:
        years_by_c.setdefault(c, []).append(d.years[i])
items = []
for r in read("region_trend.csv"):
    y = int(r["year"])
    idx = [c["country"] for c in d.countries if r["region"] == "All regions" or c["who_region"] == r["region"]]
    one = 100 * sum(1 for c in idx if c in years_by_c and min(years_by_c[c]) <= y) / len(idx)
    two = 100 * sum(1 for c in idx if len(years_by_c.get(c, [])) >= 2 and sorted(years_by_c[c])[1] <= y) / len(idx)
    items += [(f"{r['region']} {y} >=1", float(r["at_least_one"]), one, 0.05),
              (f"{r['region']} {y} >=2", float(r["two_or_more"]), two, 0.05)]
all_pass(f"Region profiles region_trend.csv: country coverage to {LAST_FULL_YEAR}", items)

# ---- leading-function map ----------------------------------------------------------------
items = []
for r in read("leading_function.csv"):
    ss = [i for i in cstud.get(r["country"], ()) if d.named_functions[i]]
    cnt = Counter(f for i in ss for f in d.named_functions[i]).most_common()
    lead = [f for f, k in cnt if k == cnt[0][1]] if cnt else []
    status = ("none" if not cstud.get(r["country"]) else "few" if len(ss) < 5 else "tie" if len(lead) > 1 else "lead")
    items.append((r["country"], f"{r['status']}:{r['leading_function']}",
                  f"{status}:{lead[0] if status == 'lead' else ''}", None))
all_pass("Leading-function map leading_function.csv: status and leading function", items)

# ---- figure 8: aid vs research -----------------------------------------------------------
av = read("aid_vs_research.csv")
src = (HERE / "prep_data.py").read_text(encoding="utf-8")
ns = {}
exec(src[src.index("def gbd_bucket"):src.index("bucket = [")], ns)
bucket = {c["country"]: ns["gbd_bucket"](c["income"], c["un_region"]) for c in d.countries}
pairs_by_bucket = Counter(bucket[c] for cs in d.study_countries for c in cs)
tot = sum(pairs_by_bucket.values())
all_pass("Fig 8 aid_vs_research.csv: research shares (distinct pairs)", [
    (r["region"], float(r["research_share"]), 100 * pairs_by_bucket[r["region"]] / tot, 0.1) for r in av],
    note="tolerance 0.1 pp: the CSV counts site pairs (see the pairs check above)")
f04 = pd.read_excel(DOCS / "dex_hff" / "F04_DAH_by_GBD_super-region_forecast_2015-2030.xlsx", sheet_name="in")
f04 = f04[f04["Year"].isin([2022, 2023, 2024])].groupby("Super-region")["Development assistance for health (DAH) received"].mean()
all_pass("Fig 8 aid_vs_research.csv: aid shares", [
    (r["region"], float(r["aid_share"]), 100 * f04.get(r["region"], 0) / f04.sum(), 0.05) for r in av])

# ---- numbers typed into the R scripts ----------------------------------------------------
for script in sorted(HERE.glob("*.R")):
    text = script.read_text(encoding="utf-8")
    for var, data_val in [("MS_COUNTRIES", len(d.countries_named())), ("MS_PAIRS", d.pairs())]:
        for v in re.findall(rf"^{var} <- (\d+)", text, flags=re.M):
            info(f"{script.name}: {var}", v, f"{data_val:,} in the data",
                 "typed in from the manuscript text; differs from the data drawn in the figure")

report("Figure audit", rows, HERE / "audit_figures_report.md")
