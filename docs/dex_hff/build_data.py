"""Builds docs/data/*.json for the HFF dashboard from the extraction CSV + summary workbook.

Inputs:
  docs/dex_hff/hff_pipeline_full_single_model.csv   (52,826 records, *_final consensus columns)
  docs/dex_hff/hff_pipeline_summary.xlsx            (Stage Funnel sheet -> content.json funnel)

Outputs (docs/data/):
  dict.json, studies.json, function.json, outcome.json, geo.json, countries.json, content.json

Run: python docs/dex_hff/build_data.py
"""
import json
import re
from collections import Counter
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # docs/
DEX = ROOT / "dex_hff"
DATA = ROOT / "data"
BUILD_DATE = "2026-09-15"

UNCLEAR = "Unclear"

# ---------------------------------------------------------------------------
# Load inputs
# ---------------------------------------------------------------------------
csv_path = DEX / "hff_pipeline_full_single_model.csv"
df = pd.read_csv(csv_path)

wb = openpyxl.load_workbook(DEX / "hff_pipeline_summary.xlsx", data_only=True)
funnel_ws = wb["Stage Funnel"]
funnel_rows_raw = [r for r in funnel_ws.iter_rows(min_row=2, values_only=True) if r[0] is not None]

n_extracted = len(df)  # Stage 0 input, 52,826

# Analysis population = records that passed the bucket screen and had extraction attempted.
pop = df[df["total_calls"].notna()].reset_index(drop=True)
n_studies = len(pop)
print(f"Total input (Stage 0): {n_extracted}")
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
has_doi = pop["doi"].notna().astype(int)
year = pop["year"].astype(int)


def era_of(y):
    return "2010-2017" if y <= 2017 else "2018-2026"


era = year.map(era_of)

# ---------------------------------------------------------------------------
# Geography: parse geo_final, match against the reused country reference
# ---------------------------------------------------------------------------
existing_countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
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
    for name in matched:
        geo_s.append(i)
        geo_c.append(name_to_idx[name])
        geo_y.append(int(year.iloc[i]))
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
}

function_json = {"s": func_s, "g": func_g}
outcome_json = {"s": outcome_s, "g": outcome_g}
geo_json = {"s": geo_s, "c": geo_c, "y": geo_y}

# ---------------------------------------------------------------------------
# dict.json
# ---------------------------------------------------------------------------
existing_dict = json.loads((DATA / "dict.json").read_text(encoding="utf-8"))

pct_quant = round(100 * (type_of_analysis == "Quantitative").mean(), 1)
pct_doi = round(100 * has_doi.mean(), 1)
pct_single = round(100 * (geo_scope == "Single country").mean(), 1)

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
        "un_region": existing_dict["levels"]["un_region"],
        "iso3": existing_dict["levels"]["iso3"],
        "country": existing_dict["levels"]["country"],
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
    "REGIONS": existing_dict["REGIONS"],
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
    label, count, pct_total, pct_prior = row
    label = str(label).strip()
    is_top = label.startswith("Stage") and "input" in label
    strong = label.strip().startswith("Stage 0") or "clean" in label.lower()
    indent = "— " if label.startswith("  ->") else ("  — " if label.startswith("      ") else "")
    clean_label = label.replace("  -> ", "").replace("      ", "").strip()
    funnel_content.append({
        "label": indent + clean_label,
        "records": fmt(count) if isinstance(count, (int, float)) else str(count),
        "strong": bool(strong),
    })

hero = [
    {"text": "This app maps the global evidence base on health financing functions — studies "
             "that analyse how health systems raise, pool, allocate and spend money. ",
     "strong": False, "em": False},
    {"text": fmt(n_extracted), "strong": True, "em": False},
    {"text": " records were screened; ", "strong": False, "em": False},
    {"text": fmt(n_studies), "strong": True, "em": False},
    {"text": " passed the bucket screen and were fully extracted by the LLM classification "
             "pipeline. The ", "strong": False, "em": False},
    {"text": "Explorer", "strong": False, "em": True},
    {"text": " crosses any variables in the corpus, the ", "strong": False, "em": False},
    {"text": "Country profile", "strong": False, "em": True},
    {"text": " opens a single setting, and ", "strong": False, "em": False},
    {"text": "Methods", "strong": False, "em": True},
    {"text": " explains how the map is built.", "strong": False, "em": False},
]

glance_tiles = [
    {"label": "Records analysed", "value": fmt(n_studies), "theme": "primary", "sub": None},
    {"label": "Years covered", "value": "2010–2026", "theme": "secondary", "sub": None},
    {"label": "Countries studied", "value": fmt(n_countries_with_studies), "theme": "info",
     "sub": "named in extracted geography"},
    {"label": "Financing functions coded", "value": fmt(len(function_grps)), "theme": "secondary", "sub": None},
    {"label": "Quantitative analysis", "value": f"{pct_quant:.0f}%", "theme": "success", "sub": None},
    {"label": "Has a recovered DOI", "value": f"{pct_doi:.0f}%", "theme": "info", "sub": None},
    {"label": "Single-country studies", "value": f"{pct_single:.0f}%", "theme": "secondary", "sub": None},
]

content_json = {
    "hero": hero,
    "glance_tiles": glance_tiles,
    "funnel": funnel_content,
    "registries": {
        "trend_vars": [
            {"label": "Income group", "column": "income"},
            {"label": "UN region", "column": "un_region"},
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
write_json("content.json", content_json)

old_disease = DATA / "disease.json"
if old_disease.exists():
    old_disease.unlink()
    print("removed stale disease.json (replaced by function.json + outcome.json)")

print("\nFinancing function categories:", function_grps)
print("\nOutcome domain categories:", outcome_grps)
print(f"\nCountries with >=1 study: {n_countries_with_studies}")
