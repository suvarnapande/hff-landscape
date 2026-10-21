"""[v2.5 copy of build_data_v2_4.py: reads the HFF dataset v2.5.1 (v2_5_1/hff_v2_5_1_site.csv); otherwise unchanged.]

Builds docs/data/*.json for the HFF dashboard from the HFF dataset v2.5.1.

v2.4 copy of build_data_v2_2.py (itself a copy of build_data_v5.py). Differences from the v5 build:
  - input is v2_5_1/hff_v2_5_1_site.csv (made by make_v2_5_csv.py from the v2.5.1 analysis file):
    every row is an included study, so n_extracted == n_studies
  - the financing function is the v52 label (financing_function_v52)
  - the Methods funnel is the v2.5.1 selection flow, read from v2_5_1/PRISMA_v2_5_1.json

Inputs:
  docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv
  docs/dex_hff/v2_5_1/PRISMA_v2_5_1.json

Outputs (docs/data/):
  dict.json, studies.json, function.json, outcome.json, geo.json, countries.json, content.json

Run: python scripts/build_data_v2_5.py  (after make_v2_5_csv.py)
"""
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "docs"  # docs/
DEX = ROOT / "dex_hff"
DATA = ROOT / "data"
BUILD_DATE = "2026-10-13"
SOURCE_NAME = "HFF dataset v2.5.1"

UNCLEAR = "Unclear"

# ---------------------------------------------------------------------------
# Load inputs
# ---------------------------------------------------------------------------
csv_path = DEX / "v2_5_1" / "hff_v2_5_1_site.csv"
df = pd.read_csv(csv_path, low_memory=False)

n_extracted = len(df)  # every record in the v5 file

# Analysis population = every v5 record (v5 carries no bucket-screen columns).
pop = df.reset_index(drop=True)
n_studies = len(pop)


def has_usable_value(series):
    values = series.fillna("").astype(str).str.strip().str.lower()
    missing_markers = {"", "nan", "none", "could not find", "not found", "n/a", "na"}
    return ~values.isin(missing_markers)

has_doi = has_usable_value(pop["doi"]).astype(int)
has_url = has_usable_value(pop["url"]).astype(int)
has_publication_link = ((has_doi == 1) | (has_url == 1)).astype(int)

# Funnel = the v2.2 selection flow. The upstream screening counts are not in the PRISMA
# file; they are the ones stated in V2_2_DATASET_README.md ("Selection flow").
prisma = json.loads((DEX / "v2_5_1" / "PRISMA_v2_5_1.json").read_text(encoding="utf-8"))
assert prisma["reconciles"], "PRISMA_v2_5_1.json does not reconcile"
routes = prisma["routes"]
excl = prisma["excluded"]
n_pool = prisma["pool_total"]
n_included = prisma["included"]
assert n_included == n_studies, f"PRISMA includes {n_included}, the site build has {n_studies}"
n_second_opinion = int((pop["function_label_source"] == "second_opinion").sum())
n_excl_other = sum(v for k, v in excl.items()
                   if k not in ("no_financing_function_at_relabel", "no_abstract", "duplicate", "placeholder",
                                "duplicate_doi", "published_before_2010"))
funnel_rows_raw = [
    ("Stage 0: Records identified", 1_154_050),
    ("      No abstract in any source (not screened)", 56_327),
    ("  -> Screened at title and abstract", 1_097_723),
    ("Stage 1: Records entering the final selection", n_pool),
    ("  -> September include set", routes["v1_include"]["entering_pool"]),
    ("  -> October targeted re-screen", routes["v11.2_rescreen"]["in_under_11b"]),
    ("  -> Unsure at the original screening", routes["unsure_original_screening"]["entering_pool"]),
    ("  -> Unsure at the September second-pass screening", routes["pass2_unsure"]["entering_pool"]),
    ("  -> Included at the first pass, missing from the second pass", routes["dropped_before_pass2"]["entering_pool"]),
    ("      Excluded: no financing function", excl["no_financing_function_at_relabel"]),
    ("      Excluded: no abstract", excl["no_abstract"]),
    ("      Excluded: duplicate (same title and year)", excl["duplicate"]),
    # v2.4: duplicates found once DOIs existed for every route (Decision 16)
    ("      Excluded: duplicate (same DOI)", excl["duplicate_doi"]),
    ("      Excluded: placeholder or series title", excl["placeholder"]),
    ("      Excluded: other reasons", n_excl_other),
    # v2.2.1: three studies with no year at the EPPI import, later found to be December 2009
    # publications; excluded by the 2010-onwards criterion (make_v2_2_1.py)
    ("      Excluded: published before 2010 (no year at import)", excl["published_before_2010"]),
    ("Stage 2: Studies included", n_included),
    ("  -> Financing function from the second-opinion check", n_second_opinion),
]
assert sum(r["entering_pool"] if "entering_pool" in r else r["in_under_11b"] for r in routes.values()) == n_pool
print(f"Included studies in v2.5.1: {n_included}; in the site build: {n_studies}")
print(f"Analysis population (extraction attempted): {n_studies}")

# ---------------------------------------------------------------------------
# studies.json — scalar per-record coded columns
# ---------------------------------------------------------------------------
def fill_unclear(s):
    return s.fillna(UNCLEAR).astype(str)

study_design = fill_unclear(pop["study_design_final"])
type_of_analysis = fill_unclear(pop["type_of_analysis_deduced_final"])
data_type = fill_unclear(pop["data_type_final"])
data_source = fill_unclear(pop["data_source_final"])
unit_of_observation = fill_unclear(pop["unit_of_observation_final"])
year = pop["year"].astype(int)


def era_of(y):
    return "2010-2017" if y <= 2017 else "2018-2026"


era = year.map(era_of)

# ---------------------------------------------------------------------------
# Geography: parse geo_final, match against the reused country reference
# ---------------------------------------------------------------------------
existing_countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
# v2.2: 31 countries the v2.2 studies name that the inherited list lacked, from
# make_country_additions_v2_2.py (UN population, World Bank spending; no DALYs yet, see
# DATA_GAPS_v2_5.md). Appended once: after the first run they are already in countries.json.
# Values filled in the CSV later (e.g. GBD DALYs) also reach rows added on an earlier run.
_by_iso3 = {c["iso3"]: c for c in existing_countries}
for _r in pd.read_csv(DEX / "country_additions_v2_2.csv", dtype={"iso3": str}).to_dict("records"):
    _row = {
        "iso3": _r["iso3"], "country": _r["country"], "income": _r["income"], "un_region": _r["un_region"],
        "pop": int(_r["pop"]) if pd.notna(_r["pop"]) else None,
        "dalys": float(_r["dalys"]) if pd.notna(_r["dalys"]) else None,
        "total_spend_bn": float(_r["total_spend_bn"]) if pd.notna(_r["total_spend_bn"]) else None,
    }
    if _r["iso3"] in _by_iso3:
        _by_iso3[_r["iso3"]].update({k: v for k, v in _row.items() if v is not None})
    else:
        existing_countries.append(_row)
# Regions (country_regions_v2_4.csv, from make_country_regions_v2_4.py): the site uses WHO regions
# (who_region); un_region (UN M49, the earlier classification) and wb_region are kept, archived.
_regions = {r["iso3"]: r for r in pd.read_csv(DEX / "country_regions_v2_4.csv", dtype=str,
                                                  keep_default_na=False).to_dict("records")}
for _c in existing_countries:
    _reg = _regions.get(_c["iso3"])
    assert _reg, f"{_c['iso3']} is missing from country_regions_v2_4.csv; rerun make_country_regions_v2_4.py"
    _c["who_region"] = _reg["who_region"] or None
    _c["who_region_source"] = _reg["who_region_source"]
    _c["wb_region"] = _reg["wb_region"] or None
ref_by_name = {c["country"]: c for c in existing_countries}
ref_by_iso3 = {c["iso3"]: c for c in existing_countries}

ALIASES = {
    "united states": "United States of America", "usa": "United States of America",
    "u.s.": "United States of America", "u.s.a.": "United States of America",
    "uk": "United Kingdom", "great britain": "United Kingdom", "england": "United Kingdom",
    "scotland": "United Kingdom", "wales": "United Kingdom", "northern ireland": "United Kingdom",
    "czech republic": "Czechia", "cote d'ivoire": "Ivory Coast", "côte d'ivoire": "Ivory Coast",
    "dr congo": "Democratic Republic of the Congo",
    "democratic republic of congo": "Democratic Republic of the Congo",
    "congo, dem. rep.": "Democratic Republic of the Congo",
    "congo-kinshasa": "Democratic Republic of the Congo",
    "republic of congo": "Republic of the Congo", "congo-brazzaville": "Republic of the Congo",
    "congo, rep.": "Republic of the Congo",
    "tanzania": "United Republic of Tanzania", "united republic of tanzania": "United Republic of Tanzania",
    "eswatini": "eSwatini", "swaziland": "eSwatini",
    "macedonia": "North Macedonia", "fyrom": "North Macedonia",
    "serbia": "Republic of Serbia",
    "timor-leste": "East Timor",
    "myanmar (burma)": "Myanmar", "burma": "Myanmar",
    "hong kong": "Hong Kong S.A.R.", "hong kong sar": "Hong Kong S.A.R.",
    "uae": "United Arab Emirates", "u.a.e.": "United Arab Emirates",
    "south korea": "South Korea", "republic of korea": "South Korea", "korea, south": "South Korea",
    "north korea": "North Korea", "korea, north": "North Korea",
    "laos": "Laos", "lao pdr": "Laos", "lao people's democratic republic": "Laos",
    "vatican city": None, "vatican": None,
    "türkiye": "Turkey", "turkiye": "Turkey",
    "viet nam": "Vietnam",
    "russian federation": "Russia",
    "slovak republic": "Slovakia",
    # v2.2 spellings of countries already in the reference ("Korea": all 54 studies are
    # high-income and about South Korea; "Congo" is left out, it could be either Congo)
    "korea": "South Korea",
    "kyrgyz republic": "Kyrgyzstan",
    "the gambia": "Gambia",
    "the netherlands": "Netherlands",
    "republic of moldova": "Moldova",
    # spellings of the countries added from country_additions_v2_2.csv
    "occupied palestinian territory": "Palestine",
    "brunei darussalam": "Brunei",
    "federated states of micronesia": "Micronesia",
}


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


ALIASES = {norm(k): v for k, v in ALIASES.items()}
name_lookup = {norm(n): n for n in ref_by_name}


def match_country(token):
    t = token.strip()
    if not t:
        return None
    key = norm(t)
    if key in ALIASES:
        return ALIASES[key]
    if key in name_lookup:
        return name_lookup[key]
    return None


geo_s, geo_c, geo_y = [], [], []
# Income group of each study-country pair in the publication year, from v2.2's
# income_level_bundled (World Bank classification in the publication year; "MIC" = upper
# middle). That field lists the distinct groups of the countries a study names, not one per
# country, so: one group listed -> every country of the study gets it. No value (mostly 2026
# studies: v2.2's lookup stops at 2025), or several groups -> the World Bank's historical
# classification (OGHIST_wb_income_history.xlsx, fiscal year Y+1 = published July of the
# publication year Y, the convention that best matches v2.2: 97.9% of single-country studies);
# where that has no value (publications 2025-26: the file runs to FY2025), the current (FY2027) group from
# countries.json. geo.json "i" indexes dict levels.income (-1 = no group). Used by the
# Explorer's income filter and breakdowns and the income figures.
INCOME_LV = ["Low income", "Lower middle income", "Upper middle income", "High income"]
PUB_INCOME = {"LIC": "Low income", "LMIC": "Lower middle income", "MIC": "Upper middle income", "HIC": "High income"}
geo_i = []
n_pub_income = Counter()
_oghist = pd.read_excel(DEX / "OGHIST_wb_income_history.xlsx", sheet_name="Country Analytical History",
                        header=None)
_fy_col = {j: 2000 + int(str(v)[2:]) if int(str(v)[2:]) < 80 else 1900 + int(str(v)[2:])
           for j, v in enumerate(_oghist.iloc[4]) if str(v).startswith("FY")}
_OGHIST_GROUP = {"L": "Low income", "LM": "Lower middle income", "UM": "Upper middle income", "H": "High income"}
wb_income_history = {}  # (iso3, fiscal year) -> group
for _, _row in _oghist.iloc[11:].iterrows():
    if isinstance(_row[0], str) and len(_row[0]) == 3:
        for j, fy in _fy_col.items():
            if str(_row[j]).strip() in _OGHIST_GROUP:
                wb_income_history[(_row[0], fy)] = _OGHIST_GROUP[str(_row[j]).strip()]
unmatched = Counter()
country_order = list(ref_by_name.keys())  # preserves existing countries.json row order
name_to_idx = {n: i for i, n in enumerate(country_order)}

geo_scope_vals = []
for i, raw in enumerate(pop["geo_final"]):
    if pd.isna(raw):
        geo_scope_vals.append("No country stated")
        continue
    tokens = [t.strip() for t in str(raw).split(",") if t.strip()]
    matched = []
    for tok in tokens:
        name = match_country(tok)
        if name is not None:
            matched.append(name)
        elif name is None and norm(tok) not in ALIASES:
            unmatched[tok] += 1
    pub = pop["income_level_bundled"].iloc[i]
    pub_groups = {g.strip() for g in str(pub).split(";") if g.strip()} if pd.notna(pub) else set()
    for name in matched:
        geo_s.append(i)
        geo_c.append(name_to_idx[name])
        geo_y.append(int(year.iloc[i]))
        hist = wb_income_history.get((ref_by_name[name]["iso3"], int(year.iloc[i]) + 1))
        if len(pub_groups) == 1:
            inc = PUB_INCOME[next(iter(pub_groups))]
            n_pub_income["publication year (v2.4)"] += 1
        elif hist:
            inc = hist
            n_pub_income["publication year (World Bank history, filling a v2.4 gap)"] += 1
        else:
            inc = ref_by_name[name].get("income")
            n_pub_income["current (2025-26 publications or not in World Bank history)"] += 1
        geo_i.append(INCOME_LV.index(inc) if inc in INCOME_LV else -1)
    if len(matched) >= 2:
        geo_scope_vals.append("Multi-country")
    elif len(matched) == 1:
        geo_scope_vals.append("Single country")
    else:
        geo_scope_vals.append("Region/global")

geo_scope = pd.Series(geo_scope_vals)

print(f"\ngeo.json rows (study x country pairs): {len(geo_s)}")
print(f"Distinct unmatched geography tokens: {len(unmatched)}")
print("Top 40 unmatched tokens (left out of geo.json, study still counted elsewhere):")
for tok, cnt in unmatched.most_common(40):
    print(f"   {tok!r}: {cnt}")

# ---------------------------------------------------------------------------
# Recompute countries.json study counts + ratios from the new geo.json
# ---------------------------------------------------------------------------
counts = Counter(geo_c)
new_countries = []
for i, name in enumerate(country_order):
    r = dict(ref_by_name[name])
    n = counts.get(i, 0)
    dalys = r.get("dalys")
    spend = r.get("total_spend_bn")
    pop_n = r.get("pop")
    r["studies"] = n
    r["per100k_dalys"] = (n / (dalys / 1e5)) if (dalys not in (None, 0)) else (0 if n == 0 else None)
    r["per_bn_usd"] = (n / spend) if (spend not in (None, 0)) else (0 if n == 0 else None)
    r["per_million"] = (n / (pop_n / 1e6)) if (pop_n not in (None, 0)) else (0 if n == 0 else None)
    new_countries.append(r)

n_countries_with_studies = sum(1 for r in new_countries if r["studies"] > 0)

# ---------------------------------------------------------------------------
# function.json / outcome.json — multi-value junction tables
# ---------------------------------------------------------------------------
def split_multi(series):
    return series.fillna("").apply(lambda s: [t.strip() for t in s.split(";") if t.strip()])


FUNCTION_DROP = {"NA"}
OUTCOME_DROP = {"NA"}

func_lists = split_multi(pop["financing_function_final"])
outcome_lists = split_multi(pop["outcome_domain_final"])

function_grps = sorted({v for lst in func_lists for v in lst if v not in FUNCTION_DROP})
outcome_grps = sorted({v for lst in outcome_lists for v in lst if v not in OUTCOME_DROP})
func_idx = {v: i for i, v in enumerate(function_grps)}
outcome_idx = {v: i for i, v in enumerate(outcome_grps)}

func_s, func_g = [], []
for i, lst in enumerate(func_lists):
    for v in lst:
        if v in func_idx:
            func_s.append(i)
            func_g.append(func_idx[v])

outcome_s, outcome_g = [], []
for i, lst in enumerate(outcome_lists):
    for v in lst:
        if v in outcome_idx:
            outcome_s.append(i)
            outcome_g.append(outcome_idx[v])

# ---------------------------------------------------------------------------
# Write studies.json (columnar / SoA)
# ---------------------------------------------------------------------------
def levels_of(series):
    return sorted(series.unique().tolist())


LV_STUDY_DESIGN = levels_of(study_design)
LV_TYPE_OF_ANALYSIS = levels_of(type_of_analysis)
LV_DATA_TYPE = levels_of(data_type)
LV_DATA_SOURCE = levels_of(data_source)
LV_UNIT_OF_OBSERVATION = levels_of(unit_of_observation)
LV_GEO_SCOPE = ["Multi-country", "No country stated", "Region/global", "Single country"]
LV_ERA = ["2010-2017", "2018-2026"]

code_of = {
    "study_design": {v: i for i, v in enumerate(LV_STUDY_DESIGN)},
    "type_of_analysis": {v: i for i, v in enumerate(LV_TYPE_OF_ANALYSIS)},
    "data_type": {v: i for i, v in enumerate(LV_DATA_TYPE)},
    "data_source": {v: i for i, v in enumerate(LV_DATA_SOURCE)},
    "unit_of_observation": {v: i for i, v in enumerate(LV_UNIT_OF_OBSERVATION)},
    "geo_scope": {v: i for i, v in enumerate(LV_GEO_SCOPE)},
    "era": {v: i for i, v in enumerate(LV_ERA)},
}

studies_json = {
    "id": pop["record_id"].astype(int).tolist(),
    "year": year.tolist(),
    "study_design": [code_of["study_design"][v] for v in study_design],
    "type_of_analysis": [code_of["type_of_analysis"][v] for v in type_of_analysis],
    "data_type": [code_of["data_type"][v] for v in data_type],
    "data_source": [code_of["data_source"][v] for v in data_source],
    "unit_of_observation": [code_of["unit_of_observation"][v] for v in unit_of_observation],
    "geo_scope": [code_of["geo_scope"][v] for v in geo_scope],
    "era": [code_of["era"][v] for v in era],
    "has_doi": has_doi.tolist(),
    "has_publication_link": has_publication_link.tolist(),
}

function_json = {"s": func_s, "g": func_g}
outcome_json = {"s": outcome_s, "g": outcome_g}
geo_json = {"s": geo_s, "c": geo_c, "y": geo_y, "i": geo_i}
print("Income group of study-country pairs:", dict(n_pub_income))

# ---------------------------------------------------------------------------
# dict.json
# ---------------------------------------------------------------------------
existing_dict = json.loads((DATA / "dict.json").read_text(encoding="utf-8"))

pct_quant = round(100 * (type_of_analysis == "Quantitative").mean(), 1)
pct_link = round(100 * has_publication_link.mean(), 1)
pct_single = round(100 * (geo_scope == "Single country").mean(), 1)
pct_doi = round(100 * has_doi.mean(), 1)

dict_json = {
    "levels": {
        "study_design": LV_STUDY_DESIGN,
        "type_of_analysis": LV_TYPE_OF_ANALYSIS,
        "data_type": LV_DATA_TYPE,
        "data_source": LV_DATA_SOURCE,
        "unit_of_observation": LV_UNIT_OF_OBSERVATION,
        "geo_scope": LV_GEO_SCOPE,
        "era": LV_ERA,
        "income": existing_dict["levels"]["income"],
        "un_region": sorted({c["un_region"] for c in new_countries if c["un_region"]}),  # archived
        "who_region": sorted({c["who_region"] for c in new_countries if c["who_region"]}),
        "iso3": [c["iso3"] for c in new_countries],
        "country": [c["country"] for c in new_countries],
    },
    "meta": {
        "n_extracted": n_extracted,
        "n_studies": n_studies,
        "n_countries": n_countries_with_studies,
        "n_countries_named": len({c for c in geo_c}),
        "pct_full": round(100 * n_studies / n_extracted, 1),
        "pct_quant": pct_quant,
        "pct_doi": pct_doi,
        "pct_single": pct_single,
        "years": [2010, 2026],
        "built": BUILD_DATE,
        "inc_lv": existing_dict["meta"]["inc_lv"],
        "pal_inc": existing_dict["meta"]["pal_inc"],
    },
    "REGIONS": sorted({c["who_region"] for c in new_countries if c["who_region"]}),  # WHO regions
    "financing_function_grps": function_grps,
    "outcome_domain_grps": outcome_grps,
    "years": [2010, 2026],
}

# ---------------------------------------------------------------------------
# content.json
# ---------------------------------------------------------------------------
def fmt(n):
    return f"{n:,}"


funnel_content = []
for row in funnel_rows_raw:
    label, count = row
    label = str(label)
    strong = label.startswith("Stage")
    indent = "— " if label.startswith("  ->") else ("  — " if label.startswith("      ") else "")
    clean_label = label.replace("  -> ", "").replace("      ", "").strip()
    funnel_content.append({
        "label": indent + clean_label,
        "records": fmt(count) if isinstance(count, (int, float)) else str(count),
        "strong": bool(strong),
    })

hero = [
    {"text": "The HSF Evidence Map brings together more than 53,000 studies on how health "
             "systems raise, pool and spend money. Explore what has been studied, where evidence "
             "is concentrated, how the field is changing, and which countries and health financing "
             "priorities remain underexplored.",
     "strong": False, "em": False},
]

# Tile labels are the keys app.js uses to order the Overview cards and pick their display copy
# (tileOrder, OVERVIEW_TILE_COPY); keep them, or the cards change order.
glance_tiles = [
    {"label": "Records analysed", "value": fmt(n_studies), "theme": "primary", "sub": None},
    {"label": "Years covered", "value": "2010–2026", "theme": "secondary", "sub": None},
    {"label": "Countries studied", "value": fmt(n_countries_with_studies), "theme": "info",
     "sub": "named in extracted geography"},
    {"label": "Financing functions coded", "value": fmt(len(function_grps)), "theme": "secondary", "sub": None},
    {"label": "Quantitative analysis", "value": f"{pct_quant:.0f}%", "theme": "success", "sub": None},
    {"label": "Has a recovered DOI", "value": f"{pct_link:.0f}%", "theme": "info", "sub": None},
    {"label": "Single-country studies", "value": f"{pct_single:.0f}%", "theme": "secondary", "sub": None},
]

content_json = {
    "hero": hero,
    "glance_tiles": glance_tiles,
    "funnel": funnel_content,
    "registries": {
        "trend_vars": [
            {"label": "Income group (in publication year)", "column": "income"},
            {"label": "Region (WHO)", "column": "who_region"},
            {"label": "Financing function", "column": "func_grp"},
            {"label": "Outcome domain", "column": "outcome_grp"},
            {"label": "Study design", "column": "study_design"},
            {"label": "Type of analysis", "column": "type_of_analysis"},
            {"label": "Data type", "column": "data_type"},
            {"label": "Data source", "column": "data_source"},
            {"label": "Geographic scope", "column": "geo_scope"},
            {"label": "Nothing (total)", "column": "none"},
        ],
        "comp_vars": [
            {"label": "Financing function", "column": "func_grp"},
            {"label": "Outcome domain", "column": "outcome_grp"},
            {"label": "Study design", "column": "study_design"},
            {"label": "Type of analysis", "column": "type_of_analysis"},
            {"label": "Data type", "column": "data_type"},
            {"label": "Data source", "column": "data_source"},
            {"label": "Unit of observation", "column": "unit_of_observation"},
            {"label": "Geographic scope", "column": "geo_scope"},
            {"label": "Era", "column": "era"},
            {"label": "Reports a DOI", "column": "doi_label"},
        ],
        "stack_vars": [
            {"label": "None", "column": ""},
            {"label": "Era", "column": "era"},
            {"label": "Type of analysis", "column": "type_of_analysis"},
            {"label": "Data type", "column": "data_type"},
            {"label": "Geographic scope", "column": "geo_scope"},
        ],
        "map_metrics": [
            {"label": "Studies", "column": "studies"},
            {"label": "Studies per 100k DALYs", "column": "per100k"},
            {"label": "Studies per US$1bn spending", "column": "per_bn"},
            {"label": "Studies per million people", "column": "per_million"},
        ],
        "scat_x": [
            {"label": "Total DALYs (GBD 2023)", "column": "dalys"},
            {"label": "Population", "column": "pop"},
            {"label": "Health spending, PPP US$bn (2022)", "column": "total_spend_bn"},
        ],
        "scat_y": [
            {"label": "Studies", "column": "studies"},
            {"label": "Studies per 100k DALYs", "column": "per100k"},
            {"label": "Studies per US$1bn spending", "column": "per_bn"},
            {"label": "Studies per million people", "column": "per_million"},
            {"label": "Health spending per person (US$ PPP)", "column": "spend_per_capita"},
        ],
        "signal_metrics": ["Quantitative", "Has DOI", "Administrative data"],
    },
}

# ---------------------------------------------------------------------------
# Write everything
# ---------------------------------------------------------------------------
def write_json(name, obj):
    path = DATA / name
    path.write_text(json.dumps(obj, allow_nan=False, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size:,} bytes)")


write_json("dict.json", dict_json)
write_json("studies.json", studies_json)
write_json("function.json", function_json)
write_json("outcome.json", outcome_json)
write_json("geo.json", geo_json)
write_json("countries.json", new_countries)
# The gallery is written by build_figures_v2_2.py and later scripts; keep it, so running
# this script on its own does not empty the Thematic analysis tab.
_old_content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
if "gallery" in _old_content:
    content_json["gallery"] = _old_content["gallery"]
write_json("content.json", content_json)

old_disease = DATA / "disease.json"
if old_disease.exists():
    old_disease.unlink()
    print("removed stale disease.json (replaced by function.json + outcome.json)")

print("\nFinancing function categories:", function_grps)
print("\nOutcome domain categories:", outcome_grps)
print(f"\nCountries with >=1 study: {n_countries_with_studies}")
