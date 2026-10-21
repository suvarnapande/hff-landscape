"""[Manuscript copy of build_glance_at_a_glance_v2_5.py (that script is kept): follows how
HSF_Interim_Manuscript_Draft_v2.0.docx calculates its numbers, like the manuscript figures in
'manuscript figures Oct 19' (make_glance_figures_v3.R):
  - headline numbers are the ones stated in the manuscript text (MS below);
  - map: studies per 10 million people ("relative to population", manuscript Figure 2);
  - region cards: function shares and n are the manuscript's Figure 4 values (single-country
    studies, FIG4 below); financial protection = share of the region's single-country studies
    with an outcome domain other than 'Unclear' (the base of the manuscript's 11%).]

[Earlier: at-a-glance copy of build_glance_regions_functions_v2_5.py (that script is kept):
  - map: studies per 100,000 DALYs (one blue ramp, log scale) instead of the leading function,
    matching the manuscript figure fig_glance_1_evidence_at_a_glance_v2;
  - the function colour key moves from the map to panel B (the cards' mix bars);
  - title without "(Un)equal weight". Still writes docs/figures/fig_glance_functions.html.]

[Earlier: financing-function copy of build_glance_regions_v2_5.py: health expenditure is dropped.
  - map: each country coloured by the financing function its studies are tagged with most
    (countries with fewer than MIN_FN_STUDIES function-tagged studies, or a tie, in grey);
  - card marker row: a stacked bar of the region's full function mix, accent = its top function;
  - writes docs/figures/fig_glance_functions.html, so fig_glance_regions.html is left as is;
  - no disease-focus row (disease groups are still computed for the console summary);
  - a "Download PNG" button saves the whole page as one image (html-to-image).]

Builds docs/figures/fig_glance_regions.html — the HFF version of HEE's
"(Un)equal weight at a glance" page: a research-intensity map plus one profile
card per WHO region (v2.4: WHO regions replace the World Bank regions of the earlier build).

HEE divides research output by disease burden (DALYs) and profiles QALY use.
HFF studies are about health financing, so here:
  - research intensity = studies per US$1bn of total health expenditure
    (countries.json `total_spend_bn`, PPP US$bn, 2022) instead of per 100,000 DALYs [dropped in this copy];
  - the "Top three" row shows financing functions (HFF has these; HEE left it blank);
  - the utility-measure row becomes "Financial protection as an outcome".

Reads docs/data/*.json plus the raw v5 CSV (only `record_id` and `mesh_theme`,
for the disease waffle). Run after build_data_v5.py:
    python scripts/build_glance_manuscript_v2_5.py
"""
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "docs"  # docs/
DATA = ROOT / "data"
FIGS = ROOT / "figures"
RAW_CSV = ROOT / "dex_hff" / "v2_5_1" / "hff_v2_5_1_site.csv"
OUT = FIGS / "fig_glance_functions.html"
SOURCE_NAME = "HFF dataset v2.5.1"
LAST_FULL_YEAR = 2025


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


dict_json = load("dict.json")
studies = load("studies.json")
function_j = load("function.json")
outcome_j = load("outcome.json")
geo_j = load("geo.json")
countries = load("countries.json")
oa_j = load("open_access_v5.json")

LV = dict_json["levels"]
FUNC_GRPS = dict_json["financing_function_grps"]
OUTCOME_GRPS = dict_json["outcome_domain_grps"]
N = len(studies["id"])
ID_TO_IDX = {sid: i for i, sid in enumerate(studies["id"])}
YEAR0, YEAR1 = min(studies["year"]), max(studies["year"])

# ---------------------------------------------------------------------------
# WHO regions, from countries.json `who_region` (build_data_v2_5.py, from
# make_country_regions_v2_4.py: WHO Global Health Observatory; places that are not WHO
# members get the WHO region of their UN M49 sub-region). The isos lists also drive the
# black silhouettes above each card; lon/lat are each silhouette's crop box.
# ---------------------------------------------------------------------------
_WHO_LAYOUT = {  # code: (name in countries.json, silhouette lon box, lat box)
    "AFR": ("African Region", [-26, 58], [-35, 38]),
    "AMR": ("Region of the Americas", [-170, -34], [-56, 72]),
    "SEAR": ("South-East Asia Region", [65, 132], [-10, 43]),
    "EUR": ("European Region", [-25, 180], [29, 78]),
    "EMR": ("Eastern Mediterranean Region", [-18, 76], [-2, 42]),
    "WPR": ("Western Pacific Region", [70, 180], [-48, 55]),
}
WB_REGIONS = {code: (name, [c["iso3"] for c in countries if c.get("who_region") == name], lon, lat)
              for code, (name, lon, lat) in _WHO_LAYOUT.items()}  # name kept from the World Bank version
TAGS = {"AFR": (20, -6), "AMR": (-90, 12), "SEAR": (82, 18), "EUR": (45, 57), "EMR": (42, 24),
        "WPR": (125, 22)}
REGION_OF = {iso: code for code, (_, isos, _, _) in WB_REGIONS.items() for iso in isos}
missing = [c["iso3"] for c in countries if c["iso3"] not in REGION_OF]
assert not missing, f"countries without a WHO region: {missing}"

# ---------------------------------------------------------------------------
# Disease categories: MeSH keyword rules copied from build_figures_v5.py
# (MESH_DISEASE_KEYWORDS / classify_disease) — keep the two in sync.
# ---------------------------------------------------------------------------
MESH_DISEASE_KEYWORDS = [
    ("Infectious", ["hiv", "human immunodeficiency virus", "acquired immunodeficiency syndrome",
        "tuberculosis", "malaria", "hepatitis", "influenza", "pneumonia", "sepsis",
        "communicable disease", "infectio", "covid-19", "sars-cov-2", "coronavirus infections",
        "measles", "cholera", "dengue", "ebola virus", "meningitis", "sexually transmitted",
        "parasitic disease", "helminthiasis", "bacterial infection", "virus disease",
        "neglected disease"]),
    ("Neoplasms", ["neoplasm", "cancer", "carcinoma", "tumor", "tumour", "leukemia", "lymphoma",
        "sarcoma", "melanoma", "oncology", "malignan"]),
    ("Cardiovascular", ["cardiovascular disease", "heart disease", "myocardial", "stroke",
        "hypertension", "coronary", "cardiac", "atrial fibrillation", "heart failure",
        "cerebrovascular", "vascular disease", "arrhythmia"]),
    ("Chronic respiratory", ["respiratory tract disease", "asthma", "pulmonary disease",
        "chronic obstructive pulmonary", "lung disease", "copd"]),
    ("Digestive", ["digestive system disease", "gastrointestinal disease", "liver disease",
        "hepatic", "cirrhosis", "pancreat", "peptic ulcer", "inflammatory bowel disease",
        "colitis", "crohn disease", "gastroenteritis", "cholelithiasis", "esophageal"]),
    ("Neurological & mental", ["nervous system disease", "neurologic", "epilepsy", "parkinson",
        "alzheimer", "dementia", "multiple sclerosis", "mental disorder", "depress",
        "anxiety disorder", "schizophrenia", "bipolar disorder", "substance-related disorder",
        "substance abuse", "mental health", "psychiatric", "autis", "attention deficit"]),
    ("Musculoskeletal", ["musculoskeletal disease", "arthritis", "osteoarthritis",
        "rheumatoid arthritis", "osteoporosis", "back pain", "joint disease", "spinal disease"]),
    ("Skin", ["skin disease", "dermatitis", "psoriasis", "eczema", "connective tissue disease",
        "lupus erythematosus", "scleroderma"]),
    ("Maternal & neonatal", ["pregnancy complication", "maternal", "neonatal", "infant, newborn",
        "perinatal", "obstetric", "postpartum", "prenatal care", "stillbirth",
        "premature birth", "congenital abnormalit", "birth defect", "infant mortality",
        "cesarean"]),
    ("Metabolic & nutritional", ["diabetes mellitus", "obesity", "malnutrition",
        "metabolic disease", "endocrine system disease", "thyroid disease",
        "nutrition disorder", "dyslipidemia", "hyperlipidemia", "metabolic syndrome"]),
    ("Injuries", ["wounds and injuries", "wound", "injuries", "fracture", "trauma",
        "poisoning", "burns", "accidental fall", "traffic accident",
        "self-injurious behavior", "occupational injur"]),
]


def classify_disease(mesh_theme):
    terms = [t.strip(" *").lower() for t in mesh_theme.split(";") if t.strip(" *")]
    scores = Counter()
    for term in terms:
        for cat, kws in MESH_DISEASE_KEYWORDS:
            if any(kw in term for kw in kws):
                scores[cat] += 1
                break
    return scores.most_common(1)[0][0] if scores else None


# Same three-way split as fig_transition in build_figures_v5.py.
COMMUNICABLE = {"Infectious", "Maternal & neonatal"}
INJURIES = {"Injuries"}

raw = pd.read_csv(RAW_CSV, low_memory=False, usecols=["record_id", "mesh_theme", "mesh_source"])
raw = raw[raw["record_id"].isin(ID_TO_IDX) & (raw["mesh_source"] == "pubmed") & raw["mesh_theme"].notna()]
disease_of = {}
for rid, mesh in zip(raw["record_id"], raw["mesh_theme"]):
    cat = classify_disease(mesh)
    if cat:
        disease_of[ID_TO_IDX[rid]] = ("comm" if cat in COMMUNICABLE else "inj" if cat in INJURIES else "ncd")

# ---------------------------------------------------------------------------
# Study-level lookups
# ---------------------------------------------------------------------------
c_iso = [c["iso3"] for c in countries]
s_countries = defaultdict(set)
for s, c in zip(geo_j["s"], geo_j["c"]):
    s_countries[s].add(c)
s_functions = defaultdict(set)
for s, g in zip(function_j["s"], function_j["g"]):
    s_functions[s].add(FUNC_GRPS[g])
s_outcomes = defaultdict(set)
for s, g in zip(outcome_j["s"], outcome_j["g"]):
    s_outcomes[s].add(OUTCOME_GRPS[g])
FP = "Financial protection"

region_studies = defaultdict(set)
for s, cs in s_countries.items():
    for c in cs:
        region_studies[REGION_OF[c_iso[c]]].add(s)

# ---------------------------------------------------------------------------
# Headline numbers
# ---------------------------------------------------------------------------
n_countries_named = sum(1 for c in countries if c["studies"] > 0)
pct_fp = 100 * sum(1 for s in range(N) if FP in s_outcomes[s]) / N
toa = LV["type_of_analysis"]
toa_known = [v for v in studies["type_of_analysis"] if toa[v] != "Unclear"]
pct_quant = 100 * sum(1 for v in toa_known if toa[v] == "Quantitative") / len(toa_known)
pct_unclear_toa = 100 * (N - len(toa_known)) / N
pct_oa = oa_j["oa_share_pct_of_doi"]
inc_of_c = [c["income"] for c in countries]
with_income = [cs for cs in s_countries.values() if any(inc_of_c[c] for c in cs)]
pct_lmic = 100 * sum(1 for cs in with_income
                     if any(inc_of_c[c] and inc_of_c[c] != "High income" for c in cs)) / len(with_income)

# ---------------------------------------------------------------------------
# Financing functions. The site palette (build_figures_v2_5.py) uses several close
# blues, which cannot be told apart on a categorical map, so this page has its own.
# ---------------------------------------------------------------------------
FUNCTION_COLORS = {
    "Revenue Raising": "#4e79a7", "Benefits decisions": "#f28e2b", "Public financial management": "#59a14f",
    "Pooling": "#b07aa1", "Purchasing": "#e15759", "Overall": "#9c755f",
    "Recurrent financing for the procurement and distribution of supply chain inputs": "#76b7b2",
    "Capital investment: infrastructure": "#edc948", "Capital investment: other health system inputs": "#ff9da7",
}
SHORT_FN = {"Recurrent financing for the procurement and distribution of supply chain inputs":
            "Recurrent financing (supply chain)",
            "Capital investment: other health system inputs": "Capital investment: other inputs",
            "Revenue Raising": "Revenue raising"}
NAMED_FUNCTIONS = [f for f in FUNC_GRPS if f not in ("Other", "Unclear")]
FN_ORDER = sorted(NAMED_FUNCTIONS, key=lambda f: -sum(1 for v in s_functions.values() if f in v))
MIN_FN_STUDIES = 5


def function_mix(ss):
    """Function-tagged studies among `ss`, and how often each named function is tagged."""
    tagged = [s for s in ss if s_functions[s] & set(NAMED_FUNCTIONS)]
    return tagged, Counter(f for s in tagged for f in s_functions[s] if f in NAMED_FUNCTIONS)


# ---------------------------------------------------------------------------
# Map: each country takes the colour of its most-tagged function.
# ---------------------------------------------------------------------------
c_studies = defaultdict(set)
for s, c in zip(geo_j["s"], geo_j["c"]):
    c_studies[c].add(s)
map_rows = []
for i, c in enumerate(countries):
    tagged, cnt = function_mix(c_studies[i])
    top = cnt.most_common()
    lead = [f for f, k in top if k == top[0][1]] if top else []
    status = ("none" if not c["studies"] else "few" if len(tagged) < MIN_FN_STUDIES
              else "tie" if len(lead) > 1 else "fn")
    map_rows.append({"iso3": c["iso3"], "country": c["country"], "n": c["studies"], "nf": len(tagged),
                     "status": status, "fn": lead[0] if status == "fn" else None,
                     "top": [[SHORT_FN.get(f, f), round(100 * k / len(tagged))] for f, k in top[:3]]})
dom_counts = Counter(r["fn"] for r in map_rows if r["fn"])

# ---------------------------------------------------------------------------
# Map (this copy): studies per 100,000 DALYs, the HEE reference's measure, on one
# blue ramp (theme_hee hee_ord) with a log scale clipped at 0.1 and 30.
# ---------------------------------------------------------------------------
RATE_MIN, RATE_MAX = 3, 1000
HEE_ORD = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95",
           "#104281", "#0d366b"]
rate_rows = [{"iso3": c["iso3"], "country": c["country"], "n": c["studies"],
              "rate": round(1e7 * c["studies"] / c["pop"], 4) if c.get("pop") and c["studies"] else None,
              "dalys": bool(c.get("pop"))} for c in countries]

# Numbers as stated in the manuscript text, and its Figure 4 (single-country studies).
MS = {"studies": 53411, "empirical_pct": 93, "countries": 198, "pairs": 47488, "named_pct": 83,
      "named": 44122, "us_pct": 29, "oa_pct": 64, "n_doi": 42144, "funder_pct": 18, "n_funder": 9501,
      "fp_pct": 11, "n_outcome": 41309}
FIG4_FN = ["Benefits decisions", "Purchasing", "Pooling", "Revenue Raising", "Public financial management",
           "Overall", "Recurrent financing for the procurement and distribution of supply chain inputs",
           "Capital investment: other health system inputs", "Capital investment: infrastructure"]
FIG4 = {  # region: (n single-country studies, shares in FIG4_FN order)
    "AFR": (3730, [22, 15, 21, 21, 19, 13, 15, 6, 5]), "AMR": (18743, [25, 27, 29, 10, 13, 5, 5, 3, 3]),
    "EMR": (1658, [20, 19, 16, 21, 15, 20, 14, 5, 5]), "EUR": (8704, [28, 26, 10, 13, 20, 12, 8, 3, 6]),
    "SEAR": (2180, [20, 12, 24, 20, 21, 12, 12, 6, 5]), "WPR": (7339, [27, 22, 23, 14, 13, 10, 9, 4, 4]),
}
n_rated = sum(1 for r in rate_rows if r["rate"])


# ---------------------------------------------------------------------------
# Region cards
# ---------------------------------------------------------------------------

def largest_remainder(counts, total=100):
    s = sum(counts.values())
    if not s:
        return {k: 0 for k in counts}
    raw_q = {k: v * total / s for k, v in counts.items()}
    out = {k: int(v) for k, v in raw_q.items()}
    for k in sorted(raw_q, key=lambda k: raw_q[k] - out[k], reverse=True)[:total - sum(out.values())]:
        out[k] += 1
    return out


def coverage_series(isos):
    """Cumulative share of `isos` named by >=1 and >=2 studies, by year."""
    idx = {i for i, iso in enumerate(c_iso) if iso in isos}
    first, second = {}, {}
    years_by_c = defaultdict(list)
    for s, c in set(zip(geo_j["s"], geo_j["c"])):
        if c in idx:
            years_by_c[c].append(studies["year"][s])
    for c, ys in years_by_c.items():
        ys = sorted(ys)
        first[c] = ys[0]
        if len(ys) >= 2:
            second[c] = ys[1]
    yrs = list(range(YEAR0, LAST_FULL_YEAR + 1))
    one = [100 * sum(1 for v in first.values() if v <= y) / len(idx) for y in yrs]
    two = [100 * sum(1 for v in second.values() if v <= y) / len(idx) for y in yrs]
    return yrs, one, two


ref_isos = set(c_iso)
_, all_one, _ = coverage_series(ref_isos)

X0, X1, Y0, Y1 = 4, 146, 70, 4


def spark_path(vals):
    step = (X1 - X0) / (len(vals) - 1)
    return " ".join(f"{'M' if i == 0 else 'L'}{X0 + i * step:.1f},{Y0 + (Y1 - Y0) * v / 100:.1f}"
                    for i, v in enumerate(vals))


def sparkline(one, two):
    ya = Y0 + (Y1 - Y0) * one[-1] / 100 + 3
    yb = Y0 + (Y1 - Y0) * two[-1] / 100 + 3
    if yb - ya < 9:
        yb = ya + 9
    return (f'<svg class="spark" viewBox="0 0 184 88" role="img" aria-label="Coverage trend">'
            f'<line x1="{X0}" x2="{X1}" y1="{Y0}" y2="{Y0}" stroke="#d9d3c7"/>'
            f'<line x1="{X0}" x2="{X1}" y1="{Y1}" y2="{Y1}" stroke="#ece6da"/>'
            f'<path d="{spark_path(all_one)}" fill="none" stroke="#b3ada3" stroke-width="2"/>'
            f'<path d="{spark_path(two)}" fill="none" stroke="#1d1d1d" stroke-width="1.6" stroke-dasharray="4 3"/>'
            f'<path d="{spark_path(one)}" fill="none" stroke="#1d1d1d" stroke-width="1.8"/>'
            f'<text x="150.0" y="{ya:.1f}">{one[-1]:.0f}%</text>'
            f'<text x="150.0" y="{yb:.1f}">{two[-1]:.0f}%</text>'
            f'<text x="4" y="86">{YEAR0}</text><text x="146" y="86" text-anchor="end">{LAST_FULL_YEAR}</text></svg>')


WAFFLE = {"comm": "#3f8f80", "ncd": "#8a63a8", "inj": "#d8a03c"}
cards = []
summary = []
for code, (name, isos, lon, lat) in WB_REGIONS.items():
    ss = region_studies[code]
    n_single, shares = FIG4[code]
    share_of = dict(zip(FIG4_FN, shares))
    tot = sum(shares)
    top_fn = max(FIG4_FN, key=share_of.get)
    top_k = share_of[top_fn]
    mix = "".join(f'<b style="width:{100 * share_of[f] / tot:.2f}%;background:{FUNCTION_COLORS[f]}" '
                  f'title="{html.escape(SHORT_FN.get(f, f))}: {share_of[f]}% of single-country studies"></b>'
                  for f in FN_ORDER if share_of[f])

    dz = Counter(disease_of[s] for s in ss if s in disease_of)

    top3 = ""
    for f in sorted(FIG4_FN, key=lambda f: -share_of[f])[:3]:
        share = share_of[f]
        top3 += (f'<div class="dz"><span class="dz-icon" style="background:{FUNCTION_COLORS[f]}"></span>'
                 f'<span class="dz-name">{html.escape(SHORT_FN.get(f, f))}</span><span class="dz-v">{share:.0f}%</span>'
                 f'<div class="dz-bar"><b style="width:{share:.1f}%;background:{FUNCTION_COLORS[f]}"></b></div></div>')

    single_cls = [s for s in ss if len(s_countries[s]) == 1 and s_outcomes[s] - {"Unclear"}]
    fp = 100 * sum(1 for s in single_cls if FP in s_outcomes[s]) / len(single_cls)
    yrs, one, two = coverage_series(set(isos))
    summary.append((code, n_single, top_fn, top_k, fp, dz))
    cards.append(f"""
      <div class="card" style="--accent:{FUNCTION_COLORS[top_fn]}">
        <div class="sil" id="sil-{code}" aria-hidden="true"></div>
        <h3>{html.escape(name)}</h3>
        <div class="tagline"><span class="tag">{code}</span> n = {n_single:,}</div>
        <div class="row row-scale">
          <div class="mix">{mix}</div>
          <div class="scale-v">Most tagged: <strong>{html.escape(SHORT_FN.get(top_fn, top_fn))}</strong></div>
        </div>
        <div class="row row-top3">{top3}</div>
        <div class="row row-utility">
          <div class="big">{fp:.0f}%</div>
          <div class="ubar"><b style="width:{fp:.1f}%"></b><span class="avg" style="left:{MS["fp_pct"]}%"></span></div>
        </div>
        <div class="row row-trend">{sparkline(one, two)}</div>
      </div>""")

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
n_disease = len(disease_of)
REGION_NAME = {k: v[0] for k, v in WB_REGIONS.items()}
n_fn_mapped = sum(dom_counts.values())
(d1, k1), (d2, k2) = dom_counts.most_common(2)
by_top = defaultdict(list)
for code, _, f, _, _, _ in summary:
    by_top[SHORT_FN.get(f, f).lower()].append(code)
LEDE = (f"In all, {MS['named']:,} studies ({MS['named_pct']}%) named at least one country, giving {MS['pairs']:,} "
        f"study-country pairs across {MS['countries']} countries and territories. {MS['us_pct']}% of studies were about "
        f"one country, the United States. Relative to population, research is densest in North America, Australia, "
        f"New Zealand and parts of northern and western Europe, and thinnest in North Africa and the Middle East, "
        f"parts of Central Africa and Central Asia.")
MAP = {
    "rows": rate_rows, "zmin": math.log10(RATE_MIN), "zmax": math.log10(RATE_MAX), "colours": HEE_ORD,
    "tags": [{"code": k, "lon": v[0], "lat": v[1]} for k, v in TAGS.items()],
    "silhouettes": {k: {"isos": v[1], "lon": v[2], "lat": v[3]} for k, v in WB_REGIONS.items()},
}


def q(note):
    return (f'<button class="q" type="button" aria-label="What does this mean?" '
            f'data-note="{html.escape(note, quote=True)}">?</button>')


MIX_NOTE = ("Each function's share of the region's single-country studies (as in the manuscript's Figure 4), "
            "scaled so the segments add up to 100%. A study can address more than one function. Colours as in the key "
            "above the cards; the card's top border takes the colour of the function studied most.")
MAP_NOTE = (f"Studies naming the country per 10 million people (World Bank population). A study naming several "
            f"countries counts in each. Log colour scale; values below {RATE_MIN:g} or above {RATE_MAX:,} take the end "
            f"colours. Grey = no study naming the country, or no population data. The manuscript reports "
            f"{MS['pairs']:,} study-country pairs across {MS['countries']} countries and territories.")
TOP3_NOTE = ("The three financing functions studied most often in the region's single-country studies, with "
             "each one's share of those studies (as in the manuscript's Figure 4). A study can address more than one "
             "function, so shares can add up to more than 100%.")
FP_NOTE = (f"Share of the region's single-country studies with a classifiable outcome (an outcome domain other "
           f"than 'Unclear') that examine financial protection (for example out-of-pocket or catastrophic health "
           f"spending). The red line is the share across all {MS['n_outcome']:,} studies with a classifiable outcome "
           f"({MS['fp_pct']}%).")
TREND_NOTE = (f"Cumulative share of the region's countries (the {len(countries)} countries in the map's country "
              f"data) named by at least one study, or by two or more, by each year. The grey line is the same for "
              f"all regions combined. The final, partial year of data ({YEAR1}) is left out.")

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Health financing research at a glance</title>
<style>
:root {{ --ink:#1d1d1d; --muted:#6b665d; --line:#d9d3c7; --bg:#f7f3ec; --card:#ece6dc; --red:#c2412d; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.45 Inter, "Segoe UI", Arial, sans-serif; }}
.wrap {{ max-width:1200px; margin:0 auto; padding:28px 24px 32px; }}
.eyebrow {{ display:flex; justify-content:space-between; align-items:center; font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--red); font-weight:700; }}
.badge {{ background:#f2dc9b; color:#5c4a12; padding:4px 10px; border-radius:4px; letter-spacing:.04em; }}
h1 {{ font:800 34px/1.12 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; font-stretch:condensed; margin:14px 0 10px; }}
.lede {{ color:#3b3832; font-size:16px; max-width:820px; margin:0 0 26px; }}
.sec {{ display:flex; align-items:center; gap:10px; margin:22px 0 6px; flex-wrap:wrap; }}
.sec b {{ background:var(--ink); color:#fff; font-size:11px; width:20px; height:20px; display:inline-flex; align-items:center; justify-content:center; border-radius:3px; }}
.sec h2 {{ font:800 20px/1 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; font-stretch:condensed; text-transform:uppercase; margin:0; }}
.sec span {{ color:var(--muted); font-size:12px; }}
.exporting .regions {{ overflow:visible; }}
.exporting #map {{ height:520px; }}
.exporting .kpis {{ grid-template-columns:repeat(6, minmax(0, 1fr)); }}
.exporting .kpi {{ border-top:0; }}
.exporting h1 {{ font-size:34px; }}
.wrap.exporting {{ padding:28px 24px 32px; }}
.eyebrow-r {{ display:flex; align-items:center; gap:10px; }}
.dl {{ padding:5px 11px; border:1px solid var(--ink); border-radius:5px; background:#fff; color:var(--ink); font:600 12px/1 Inter, "Segoe UI", Arial, sans-serif; cursor:pointer; }}
.dl:hover {{ background:var(--ink); color:#fff; }}
.dl:disabled {{ opacity:.5; cursor:wait; }}
#map {{ height:520px; }}
.kpis {{ display:grid; grid-template-columns:repeat(6, minmax(0, 1fr)); }}
.kpis-5 {{ grid-template-columns:repeat(5, minmax(0, 1fr)); border-top:1.5px solid var(--ink); border-bottom:1px solid var(--line); margin:8px 0 6px; }}
.kpi {{ padding:16px 14px 14px; border-left:1px solid var(--line); }}
.kpi:first-child {{ border-left:0; padding-left:0; }}
.kpi-v {{ font:800 36px/1 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; font-stretch:condensed; display:flex; align-items:flex-start; gap:4px; }}
.kpi-l {{ color:var(--muted); font-size:12px; margin-top:8px; }}
.regions {{ display:grid; grid-template-columns:150px repeat(6, minmax(118px, 1fr)); gap:10px; overflow-x:auto; padding-bottom:6px; }}
.labels {{ display:grid; grid-template-rows:var(--rows); padding-top:17px; }}
.lab {{ font-size:11px; color:var(--muted); padding-right:6px; }}
.lab strong {{ display:block; color:var(--ink); font:800 15px/1.1 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; text-transform:uppercase; margin-bottom:4px; }}
.lab .key {{ display:flex; align-items:center; gap:5px; }}
.lab .key i {{ width:9px; height:9px; border-radius:2px; display:inline-block; }}
.wrap {{ --rows: 62px 52px 24px 58px 140px 112px 104px; }}
.sil {{ height:58px; }}
.card {{ display:grid; grid-template-rows:var(--rows); background:var(--card); border-radius:10px; border-top:5px solid var(--accent); padding:12px 10px; min-width:0; }}
.card h3 {{ font:800 14px/1.15 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; text-transform:uppercase; text-align:center; margin:0; align-self:center; }}
.tag {{ background:var(--ink); color:#fff; font-size:10px; font-weight:700; padding:2px 5px; border-radius:3px; }}
.row-scale, .tagline {{ font-size:11px; text-align:center; color:#3b3832; }}
.mix {{ display:flex; height:12px; margin:8px 2px 6px; border-radius:3px; overflow:hidden; }}
.mix b {{ display:block; height:100%; border-right:1px solid var(--card); }}
.mix b:last-child {{ border-right:0; }}
.fn-key {{ display:flex; flex-wrap:wrap; gap:4px 14px; font-size:11.5px; color:#3b3832; margin:4px 0 2px; }}
.fn-key span {{ display:inline-flex; align-items:center; gap:5px; }}
.fn-key i {{ width:10px; height:10px; border-radius:2px; display:inline-block; }}
.scale-v {{ font-size:10.5px; color:var(--muted); }}
.waffle {{ display:grid; grid-template-columns:repeat(10, 1fr); gap:2px; width:100%; max-width:112px; margin:6px auto 0; }}
.waffle i {{ display:block; aspect-ratio:1; border-radius:50%; }}
.waffle-labels {{ display:flex; justify-content:space-around; font-size:11px; font-weight:700; margin-top:5px; }}
.waffle-n {{ font-size:10px; color:var(--muted); text-align:center; margin-top:2px; }}
.dz {{ display:grid; grid-template-columns:14px 1fr auto; gap:2px 6px; align-items:center; font-size:11px; margin-bottom:6px; }}
.dz-icon {{ width:12px; height:12px; border-radius:50%; background:#d6d0c5; grid-row:span 2; align-self:start; margin-top:2px; }}
.dz-name {{ color:var(--ink); font-weight:700; line-height:1.15; }}
.dz-v {{ color:var(--muted); font-weight:700; }}
.dz-bar {{ grid-column:2 / 4; height:4px; background:#d6d0c5; border-radius:2px; overflow:hidden; }}
.dz-bar b {{ display:block; height:100%; border-radius:2px; }}
.big {{ font:800 26px/1 "Arial Narrow", "Roboto Condensed", Inter, sans-serif; text-align:center; margin:8px 0 8px; }}
.ubar {{ position:relative; height:16px; border-radius:8px; background:#cbc5ba; overflow:visible; }}
.ubar b {{ display:block; height:100%; border-radius:8px; background:var(--ink); }}
.ubar .avg {{ position:absolute; top:-3px; width:2.5px; height:22px; margin-left:-1.25px; background:var(--red); }}
.spark {{ width:100%; height:auto; overflow:visible; }}
.spark text {{ font-size:9px; fill:#3b3832; }}
.foot {{ display:flex; justify-content:space-between; gap:24px; border-top:1px solid var(--line); margin-top:22px; padding-top:12px; font-size:11px; color:var(--muted); }}
.foot p {{ margin:0 0 4px; }}
.q {{ display:inline-flex; align-items:center; justify-content:center; width:16px; height:16px; flex:0 0 16px; padding:0; border:1px solid #8a8378; border-radius:50%; background:#fff; color:#5d574e; font:700 10px/1 Inter, Arial, sans-serif; cursor:pointer; vertical-align:middle; }}
.q:hover, .q[aria-expanded="true"] {{ background:var(--ink); color:#fff; border-color:var(--ink); }}
#pop {{ position:absolute; z-index:10; max-width:300px; padding:10px 12px; background:#fff; border:1px solid var(--line); border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,.14); font-size:12px; line-height:1.45; color:#2e2b26; display:none; }}
@media (max-width: 900px) {{ .kpis {{ grid-template-columns:repeat(3, minmax(0, 1fr)); }} .kpi {{ border-top:1px solid var(--line); }} #map {{ height:360px; }} h1 {{ font-size:26px; }} .wrap {{ padding:20px 16px 28px; }} }}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow"><span>HFF evidence map</span><span class="eyebrow-r"><button class="dl" id="page-dl" type="button" title="Download the whole page (map and region profiles) as a PNG with a citation"><span aria-hidden="true">&#10515;</span> Download PNG</button><span class="badge">Draft · data: {SOURCE_NAME}</span></span></div>
  <h1>Health financing research at a glance</h1>
  <p class="lede">{html.escape(LEDE)}</p>

  <div class="kpis kpis-5"><div class="kpi"><div class="kpi-v">{MS["studies"]:,}</div><div class="kpi-l">health financing studies, {YEAR0}–{YEAR1}</div></div><div class="kpi"><div class="kpi-v">{MS["empirical_pct"]}%{q("Studies other than literature reviews (49,800 of 53,411).")}</div><div class="kpi-l">are empirical analyses</div></div><div class="kpi"><div class="kpi-v">{MS["countries"]}{q("Countries and territories named by at least one study, as reported in the manuscript. Region or global labels (for example 'Europe' or 'Global') are not counted.")}</div><div class="kpi-l">countries or territories with at least one study</div></div><div class="kpi"><div class="kpi-v">{MS["oa_pct"]}%{q("Share of the 42,144 studies with a DOI that are open access (OpenAlex, matched by DOI).")}</div><div class="kpi-l">are open access</div></div><div class="kpi"><div class="kpi-v">{MS["funder_pct"]}%{q("Studies reporting at least one research funder (9,501 of 53,411).")}</div><div class="kpi-l">report a funder</div></div></div>
  <div class="sec"><b>A</b><h2>Geographic distribution of health financing studies</h2><span>Studies per 10 million people (log colour scale) · n = {MS["pairs"]:,} study-country pairs</span>{q(MAP_NOTE)}</div>
  <div id="map"></div>


  <div class="sec"><b>B</b><h2>Profile of studies by region</h2><span>Each card matches the black region tag on the map</span></div>
  <div class="fn-key">{"".join(f'<span><i style="background:{FUNCTION_COLORS[f]}"></i>{html.escape(SHORT_FN.get(f, f))}</span>' for f in FN_ORDER)}</div>
  <div class="regions">
    <div class="labels">
      <div></div><div></div><div></div>
      <div class="lab"><strong>Function mix {q(MIX_NOTE)}</strong>Share of single-country studies</div>
      <div class="lab"><strong>Top three financing functions {q(TOP3_NOTE)}</strong>Bar = share of single-country studies</div>
      <div class="lab"><strong>Financial protection as an outcome {q(FP_NOTE)}</strong>Black = single-country studies; red line = all studies (11%)</div>
      <div class="lab"><strong>Trend over time {q(TREND_NOTE)}</strong>% of the region's countries with a study: solid = at least 1, dashed = 2 or more, grey = all regions (at least 1)</div>
    </div>
    {"".join(cards)}
  </div>

  <div class="foot">
    <div>
      <p>Data: HFF evidence map web build ({SOURCE_NAME}); {YEAR0}–{YEAR1} publication years. Search dates: xx {q("Search dates are not in the web data; they need to come from the review protocol.")}</p>
      <p>Regions: WHO (AFR African, AMR Americas, SEAR South-East Asia, EUR European, EMR Eastern Mediterranean, WPR Western Pacific), as listed by the WHO Global Health Observatory; places that the WHO's country list does not assign to a region (Taiwan, Hong Kong, Kosovo) take the WHO region of their UN M49 sub-region. Map and trend lines cover the {len(countries)} countries in the map's country data; trends run to {LAST_FULL_YEAR}.</p>
      <p>Financing functions: the HFF financing function groups (Other and Unclear left out); a study can carry more than one. Outcome: financial protection outcome domain. Map: studies per 10 million people (World Bank population), Robinson projection; grey = no study naming the country or no population data. Headline numbers, study-country pairs and the regional function shares (single-country studies) are as reported in the HSF interim manuscript.</p>
    </div>
  </div>
</div>
<div id="pop" role="dialog"></div>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js" integrity="sha384-cCVCZkAjYNxaYKbM8lsArLznDF/SvMFr1jcZrvOpSTCa0W40ZAdLzHCEulnUa5i7" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js" integrity="sha384-UbfRVKN3/elS1r7JcK2FhmPP+KlJ4CvYwbyYD7tH+uTkbT9bNJr9eJeQ0FoFbAgz" crossorigin="anonymous"></script>
<script>
const MAP = {json.dumps(MAP, separators=(",", ":"))};
(function () {{
  const rows = MAP.rows;
  const has = rows.filter(r => r.rate > 0);
  const none = rows.filter(r => !(r.rate > 0));
  const fmt = v => v >= 10 ? v.toFixed(0) : v.toFixed(1);
  window.Plotly.newPlot("map", [
    {{ type: "choropleth", locations: has.map(r => r.iso3), z: has.map(r => Math.log10(r.rate)),
       text: has.map(r => r.country + "<br>" + r.n.toLocaleString("en-GB") + " studies<br>" + fmt(r.rate) +
         " per 10 million people"), hoverinfo: "text",
       zmin: MAP.zmin, zmax: MAP.zmax, colorscale: MAP.colours.map((c, i) => [i / (MAP.colours.length - 1), c]),
       marker: {{ line: {{ color: "#ffffff", width: 0.4 }} }},
       colorbar: {{ title: {{ text: "per 10 million<br>people", font: {{ size: 11 }} }}, thickness: 10, len: 0.55, x: 0.02,
         y: 0.3, tickvals: [3, 10, 30, 100, 300, 1000].map(Math.log10),
         ticktext: ["3", "10", "30", "100", "300", "1,000"] }} }},
    {{ type: "choropleth", locations: none.map(r => r.iso3), z: none.map(() => 0), showscale: false,
       text: none.map(r => r.country + "<br>" + (r.dalys ? "no study naming it" : r.n.toLocaleString("en-GB") +
         " studies<br>no population data")), hoverinfo: "text", colorscale: [[0, "#dcd6cc"], [1, "#dcd6cc"]],
       marker: {{ line: {{ color: "#ffffff", width: 0.4 }} }} }},
    // Region tags: black boxes, then their white codes on top.
    {{ type: "scattergeo", lon: MAP.tags.map(t => t.lon), lat: MAP.tags.map(t => t.lat), mode: "markers",
       marker: {{ symbol: "square", size: 30, color: "#1d1d1d" }}, hoverinfo: "skip" }},
    {{ type: "scattergeo", lon: MAP.tags.map(t => t.lon), lat: MAP.tags.map(t => t.lat), mode: "text",
       text: MAP.tags.map(t => "<b>" + t.code + "</b>"), hoverinfo: "skip",
       textfont: {{ color: "#ffffff", size: 11 }} }}
  ], {{
    margin: {{ t: 0, b: 0, l: 0, r: 0 }}, showlegend: false, paper_bgcolor: "rgba(0,0,0,0)",
    font: {{ family: "Inter, Segoe UI, Arial, sans-serif" }},
    geo: {{ projection: {{ type: "robinson" }}, showframe: false, showcoastlines: false, showland: true,
           landcolor: "#e6e1d8", showcountries: true, countrycolor: "#ffffff", bgcolor: "rgba(0,0,0,0)",
           lataxis: {{ range: [-58, 85] }} }}
  }}, {{ responsive: true, displayModeBar: false }});

  // "Download PNG": the whole page (both panels) as one image via html-to-image,
  // with the site's citation line under it (same wording as figureCitation in app.js).
  const TITLE = "Health financing research at a glance";
  document.getElementById("page-dl").addEventListener("click", async e => {{
    const btn = e.currentTarget;
    btn.disabled = true;
    try {{
      // Lay the page out at its full width first, so a narrow window (or the site's
      // iframe) does not crop the region cards; restored afterwards.
      const S = 2, node = document.querySelector(".wrap");
      const plots = [...document.querySelectorAll(".js-plotly-plot")];
      const relayout = () => Promise.all(plots.map(el => window.Plotly.Plots.resize(el)));
      const frame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      node.style.width = node.style.maxWidth = "1200px";
      node.classList.add("exporting");
      let shot;
      try {{
        await relayout();
        await frame();
        shot = await window.htmlToImage.toCanvas(node, {{
          pixelRatio: S, backgroundColor: "#f7f3ec", width: node.scrollWidth, height: node.scrollHeight,
          // the live page is centred with margin:auto; without this the copied left margin
          // shifts the snapshot right and crops it in a wide window
          style: {{ margin: "0" }},
          filter: n => !(n.classList && (n.classList.contains("q") || n.classList.contains("dl")))
        }});
      }} finally {{
        node.style.width = node.style.maxWidth = "";
        node.classList.remove("exporting");
        await relayout();
      }}
      const date = new Date().toLocaleDateString("en-GB", {{ day: "numeric", month: "long", year: "numeric" }});
      const cite = "Source: 3ie (2026). Health Systems Financing (HSF) Evidence Map: " + TITLE +
        ". https://3ieimpact.pages.dev/. Downloaded " + date + ".";
      const pad = 24 * S, W = shot.width;
      const canvas = document.createElement("canvas");
      canvas.width = W;
      canvas.height = shot.height + 44 * S;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#f7f3ec";
      ctx.fillRect(0, 0, W, canvas.height);
      ctx.drawImage(shot, 0, 0);
      ctx.fillStyle = "#d9d3c7";
      ctx.fillRect(pad, shot.height, W - 2 * pad, S);
      ctx.fillStyle = "#6b665d";
      ctx.font = 12 * S + "px Inter, 'Segoe UI', Arial, sans-serif";
      ctx.textBaseline = "top";
      ctx.fillText(cite, pad, shot.height + 14 * S);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "health-financing-research-at-a-glance.png";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 2000);
    }} finally {{
      btn.disabled = false;
    }}
  }});
}})();
// Region silhouettes above each card: the region's countries filled black
// in a fixed window (same country outlines as the main map).
for (const [code, sil] of Object.entries(MAP.silhouettes)) {{
  window.Plotly.newPlot("sil-" + code, [{{
    type: "choropleth", locations: sil.isos, z: sil.isos.map(() => 1), showscale: false, hoverinfo: "skip",
    colorscale: [[0, "#1d1d1d"], [1, "#1d1d1d"]], marker: {{ line: {{ color: "#1d1d1d", width: 0.4 }} }}
  }}], {{
    margin: {{ t: 0, b: 0, l: 0, r: 0 }}, paper_bgcolor: "rgba(0,0,0,0)",
    geo: {{ visible: false, projection: {{ type: "mercator" }}, bgcolor: "rgba(0,0,0,0)",
           lonaxis: {{ range: sil.lon }}, lataxis: {{ range: sil.lat }} }}
  }}, {{ staticPlot: true, responsive: true }});
}}
// "?" notes: click to open, click elsewhere or Esc to close.
(function () {{
  const pop = document.getElementById("pop");
  let open = null;
  const close = () => {{ pop.style.display = "none"; if (open) open.setAttribute("aria-expanded", "false"); open = null; }};
  document.addEventListener("click", e => {{
    const b = e.target.closest(".q");
    if (!b) {{ if (!pop.contains(e.target)) close(); return; }}
    if (open === b) {{ close(); return; }}
    close();
    pop.textContent = b.dataset.note;
    pop.style.display = "block";
    const r = b.getBoundingClientRect();
    const left = Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - pop.offsetWidth - 12);
    pop.style.left = Math.max(8, left) + "px";
    pop.style.top = (window.scrollY + r.bottom + 6) + "px";
    b.setAttribute("aria-expanded", "true");
    open = b;
  }});
  document.addEventListener("keydown", e => {{ if (e.key === "Escape") close(); }});
}})();
</script>
</body>
</html>
"""

OUT.write_text(page, encoding="utf-8")
print(f"Wrote {OUT}")
print(f"  studies {N:,}; countries named {n_countries_named}; financial protection {pct_fp:.1f}%; "
      f"quantitative {pct_quant:.1f}% (unclear {pct_unclear_toa:.1f}%); OA {pct_oa}%; L&MICs {pct_lmic:.1f}%")
print(f"  leading function by country: {dict(dom_counts)}; ties {sum(r['status'] == 'tie' for r in map_rows)}; "
      f"too few {sum(r['status'] == 'few' for r in map_rows)}; "
      f"disease-coded {n_disease:,}")
for code, n, top_fn, top_pct, fp, dz in summary:
    tot = sum(dz.values())
    mix = " / ".join(f"{100 * dz.get(k, 0) / tot:.0f}" for k in WAFFLE) if tot else "-"
    print(f"  {code}: n={n:,}  top {SHORT_FN.get(top_fn, top_fn)} ({top_pct:.0f}% of tags)  FP {fp:.0f}%  disease comm/ncd/inj {mix} (n={tot})")
