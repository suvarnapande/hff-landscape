"""Builds the figures that are kept but HIDDEN from the HFF Thematic analysis tab:

  - fig_wellcome_priorities.png  (Wellcome priority themes, Panels A-C)
  - fig_funnel.png               (Pipeline funnel)
  - fig_design_bar.png, fig_analysis_bar.png, fig_datatype_bar.png,
    fig_datasource_bar.png       (original Methods & data bar charts)

Moved out of build_figures_v5.py so the main build only produces figures shown on
the site. Uses the same inputs and shared setup as build_figures_v5.py, writes PNGs
to docs/figures/ (or HFF_FIGS_DIR if set) and does NOT touch content.json, so these
figures never appear in the gallery.

Run: python scripts/build_hidden_figures_v5.py
"""
import json
import os
import re
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    HAVE_PLOTLY = True
except ImportError:
    HAVE_PLOTLY = False

ROOT = Path(__file__).resolve().parent.parent / "docs"  # docs/
DATA = ROOT / "data"
# HFF_FIGS_DIR / HFF_CONTENT_OUT optionally redirect outputs (e.g. for a preview run).
FIGS = Path(os.environ["HFF_FIGS_DIR"]) if os.environ.get("HFF_FIGS_DIR") else ROOT / "figures"
DEX = ROOT / "dex_hff"
# v5 copy of build_figures.py: reads the HSF extraction 29 Sept v5 file (via make_v5_csv.py)
# instead of the v2 CSV. Run after build_data_v5.py.
RAW_CSV = DEX / "hsf_extraction_29sept_v5.csv"
SOURCE_NAME = "HSF extraction 29 Sept v5"

REQUIRED_INPUTS = [
    DATA / "dict.json",
    DATA / "studies.json",
    DATA / "function.json",
    DATA / "outcome.json",
    DATA / "geo.json",
    DATA / "countries.json",
    DATA / "content.json",
    RAW_CSV,
    DEX / "topic_map.csv",
    DEX / "F03_Total_DAH_forecast_1990-2030.xlsx",
    DEX / "F07_DAH_by_source_change_2024-2025.xlsx",
    DEX / "F11_Total_health_spending_per_person_by_WB_income_group_2000-2030.xlsx",
    DEX / "F04_DAH_by_GBD_super-region_forecast_2015-2030.xlsx",
    DEX / "F12_Total_health_spending_per_person_by_country_2025.xlsx",
]

missing_inputs = [path for path in REQUIRED_INPUTS if not path.is_file()]
if missing_inputs:
    missing_list = "\n".join(f"  - {path}" for path in missing_inputs)
    raise FileNotFoundError(
        "Cannot build the complete V5 figure gallery because required input files are missing:\n"
        f"{missing_list}\n\nNo figures were generated."
    )

FIGS.mkdir(exist_ok=True)

ACCENT = "#1f5fa8"
GREY = "#adb5bd"
GOLD = "#b08d3e"
INK = "#10243e"
SUBHEAD_COLOR = "#5a6472"
PAPER = "#faf9f6"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.edgecolor": "#c9c3b3",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
})


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


dict_json = load("dict.json")
studies = load("studies.json")
function_j = load("function.json")
outcome_j = load("outcome.json")
geo_j = load("geo.json")
countries = load("countries.json")

LV = dict_json["levels"]
FUNC_GRPS = dict_json["financing_function_grps"]
OUTCOME_GRPS = dict_json["outcome_domain_grps"]
N = len(studies["id"])
N_EXTRACTED = dict_json["meta"]["n_extracted"]
ID_TO_IDX = {sid: i for i, sid in enumerate(studies["id"])}

# Legend-safe short labels for the longer financing-function names, reused by
# any figure that needs to fit a function name into an axis tick or legend.
SHORT_FN = {"Recurrent financing for the procurement and distribution of supply chain inputs": "Recurrent financing (supply chain)"}

# Harmonised financing-function palette reused across time-series, stacked-area,
# funder-mix and other function-focused figures. The four main functions follow
# the blue/teal/aqua/lavender reference supplied for the line chart.
FUNCTION_COLORS = {
    "Benefits decisions": "#1764C0",
    "Public financial management": "#2F9B92",
    "Purchasing": "#63B0BC",
    "Revenue Raising": "#93A3D0",
    "Revenue raising": "#93A3D0",
    "Pooling": "#B8C2CF",
    "Recurrent financing for the procurement and distribution of supply chain inputs": "#7E94B1",
    "Capital investment: infrastructure": "#D2B06B",
    "Capital investment: other health system inputs": "#88B7A8",
    "Other": "#B79BCB",
    "Unclear": "#D5DAE0",
}
SHORT_OUT = {"Equitable distribution of health system resources": "Equitable distribution",
             "Improved level and distribution of health": "Improved health level/dist.",
             "Efficiency in the use of resources": "Efficiency in resource use"}

# Space-constrained short labels for the longest country names, reused by any
# figure that needs a country name to fit in a tight axis tick or label.
SHORT_COUNTRY = {"Democratic Republic of the Congo": "DR Congo",
                 "United States of America": "United States",
                 "United Republic of Tanzania": "Tanzania",
                 "Central African Republic": "CAR"}

# Standard ISO 3166-1 alpha-2 -> alpha-3, for author_affiliation_countries
# (harvested as alpha-2) against countries.json's alpha-3 codes.
ISO2_TO_ISO3 = {
    "AD": "AND", "AE": "ARE", "AF": "AFG", "AG": "ATG", "AI": "AIA", "AL": "ALB", "AM": "ARM",
    "AO": "AGO", "AQ": "ATA", "AR": "ARG", "AS": "ASM", "AT": "AUT", "AU": "AUS", "AW": "ABW",
    "AX": "ALA", "AZ": "AZE", "BA": "BIH", "BB": "BRB", "BD": "BGD", "BE": "BEL", "BF": "BFA",
    "BG": "BGR", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BL": "BLM", "BM": "BMU", "BN": "BRN",
    "BO": "BOL", "BQ": "BES", "BR": "BRA", "BS": "BHS", "BT": "BTN", "BV": "BVT", "BW": "BWA",
    "BY": "BLR", "BZ": "BLZ", "CA": "CAN", "CC": "CCK", "CD": "COD", "CF": "CAF", "CG": "COG",
    "CH": "CHE", "CI": "CIV", "CK": "COK", "CL": "CHL", "CM": "CMR", "CN": "CHN", "CO": "COL",
    "CR": "CRI", "CU": "CUB", "CV": "CPV", "CW": "CUW", "CX": "CXR", "CY": "CYP", "CZ": "CZE",
    "DE": "DEU", "DJ": "DJI", "DK": "DNK", "DM": "DMA", "DO": "DOM", "DZ": "DZA", "EC": "ECU",
    "EE": "EST", "EG": "EGY", "EH": "ESH", "ER": "ERI", "ES": "ESP", "ET": "ETH", "FI": "FIN",
    "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "FR": "FRA", "GA": "GAB", "GB": "GBR",
    "GD": "GRD", "GE": "GEO", "GF": "GUF", "GG": "GGY", "GH": "GHA", "GI": "GIB", "GL": "GRL",
    "GM": "GMB", "GN": "GIN", "GP": "GLP", "GQ": "GNQ", "GR": "GRC", "GS": "SGS", "GT": "GTM",
    "GU": "GUM", "GW": "GNB", "GY": "GUY", "HK": "HKG", "HM": "HMD", "HN": "HND", "HR": "HRV",
    "HT": "HTI", "HU": "HUN", "ID": "IDN", "IE": "IRL", "IL": "ISR", "IM": "IMN", "IN": "IND",
    "IO": "IOT", "IQ": "IRQ", "IR": "IRN", "IS": "ISL", "IT": "ITA", "JE": "JEY", "JM": "JAM",
    "JO": "JOR", "JP": "JPN", "KE": "KEN", "KG": "KGZ", "KH": "KHM", "KI": "KIR", "KM": "COM",
    "KN": "KNA", "KP": "PRK", "KR": "KOR", "KW": "KWT", "KY": "CYM", "KZ": "KAZ", "LA": "LAO",
    "LB": "LBN", "LC": "LCA", "LI": "LIE", "LK": "LKA", "LR": "LBR", "LS": "LSO", "LT": "LTU",
    "LU": "LUX", "LV": "LVA", "LY": "LBY", "MA": "MAR", "MC": "MCO", "MD": "MDA", "ME": "MNE",
    "MF": "MAF", "MG": "MDG", "MH": "MHL", "MK": "MKD", "ML": "MLI", "MM": "MMR", "MN": "MNG",
    "MO": "MAC", "MP": "MNP", "MQ": "MTQ", "MR": "MRT", "MS": "MSR", "MT": "MLT", "MU": "MUS",
    "MV": "MDV", "MW": "MWI", "MX": "MEX", "MY": "MYS", "MZ": "MOZ", "NA": "NAM", "NC": "NCL",
    "NE": "NER", "NF": "NFK", "NG": "NGA", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NP": "NPL",
    "NR": "NRU", "NU": "NIU", "NZ": "NZL", "OM": "OMN", "PA": "PAN", "PE": "PER", "PF": "PYF",
    "PG": "PNG", "PH": "PHL", "PK": "PAK", "PL": "POL", "PM": "SPM", "PN": "PCN", "PR": "PRI",
    "PS": "PSE", "PT": "PRT", "PW": "PLW", "PY": "PRY", "QA": "QAT", "RE": "REU", "RO": "ROU",
    "RS": "SRB", "RU": "RUS", "RW": "RWA", "SA": "SAU", "SB": "SLB", "SC": "SYC", "SD": "SDN",
    "SE": "SWE", "SG": "SGP", "SH": "SHN", "SI": "SVN", "SJ": "SJM", "SK": "SVK", "SL": "SLE",
    "SM": "SMR", "SN": "SEN", "SO": "SOM", "SR": "SUR", "SS": "SSD", "ST": "STP", "SV": "SLV",
    "SX": "SXM", "SY": "SYR", "SZ": "SWZ", "TC": "TCA", "TD": "TCD", "TF": "ATF", "TG": "TGO",
    "TH": "THA", "TJ": "TJK", "TK": "TKL", "TL": "TLS", "TM": "TKM", "TN": "TUN", "TO": "TON",
    "TR": "TUR", "TT": "TTO", "TV": "TUV", "TW": "TWN", "TZ": "TZA", "UA": "UKR", "UG": "UGA",
    "UM": "UMI", "US": "USA", "UY": "URY", "UZ": "UZB", "VA": "VAT", "VC": "VCT", "VE": "VEN",
    "VG": "VGB", "VI": "VIR", "VN": "VNM", "VU": "VUT", "WF": "WLF", "WS": "WSM", "XK": "XKX",
    "YE": "YEM", "YT": "MYT", "ZA": "ZAF", "ZM": "ZMB", "ZW": "ZWE",
}

# research_funder is free text (7,388 distinct raw strings for fig_funder_funders.png).
# _norm_funder_key() groups case/punctuation/"&" vs. "and" variants of the same name
# together automatically (e.g. "Bill & Melinda Gates Foundation" and "Bill and Melinda
# Gates Foundation" both normalize to the same key). FUNDER_ALIASES additionally folds in
# known abbreviations and short forms that no amount of punctuation-normalizing catches.
FUNDER_ALIASES = {
    "nih": "National Institutes of Health",
    "gates foundation": "Bill and Melinda Gates Foundation",
    "who": "World Health Organization",
    "cdc": "Centers for Disease Control and Prevention",
    "nsf": "National Science Foundation",
    "dfid": "Department for International Development",
    "department for international development uk government": "Department for International Development",
    "usaid": "United States Agency for International Development",
    "world bank": "World Bank Group",
    "horizon 2020 framework programme": "Horizon 2020",
    "national social science foundation of china": "National Social Science Fund of China",
}


def _norm_funder_key(s):
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[.,\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("the "):
        s = s[4:]
    return s


FIG_META = {}  # filename -> (headline, description, finding) — single source of truth


def clean_axes(ax):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#c9c3b3")
    ax.spines["bottom"].set_color("#c9c3b3")
    ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def D(s):
    """Escape literal '$' so matplotlib doesn't treat it as mathtext delimiters
    (only in developer-authored headline/desc/finding/footnote text — never
    disabled globally, since that also breaks log-axis '10^n' tick labels)."""
    return s.replace("$", r"\$")


def set_headline(ax, headline, desc, finding, fname):
    """headline: bold claim. desc: plain, what the chart shows. finding: BOLD
    sentence with the actual numbers — matches HEE's title/subtitle convention
    exactly (plain lead-in, then a bolded finding clause)."""
    FIG_META[fname] = (headline, desc, finding)
    ax.text(0, 1.30, D(headline), transform=ax.transAxes, fontsize=16, fontweight="bold",
            color=INK, ha="left", va="bottom", linespacing=1.25)
    ax.text(0, 1.16, D(desc), transform=ax.transAxes, fontsize=10.5, color=SUBHEAD_COLOR,
            ha="left", va="bottom")
    ax.text(0, 1.02, D(finding), transform=ax.transAxes, fontsize=10.5, fontweight="bold",
            color=INK, ha="left", va="bottom")


def set_footnote(fig, text):
    fig.text(0.01, -0.02, D(text), fontsize=8.5, color=SUBHEAD_COLOR, ha="left", va="top")


def declutter_labels(ax, rows, x_col, y_col, name_col="country", fontsize=7.8, name_map=None, avoid=()):
    """Label points on a log-log scatter, greedily choosing among 32
    candidate compass-direction offsets (4 radii x 8 angles) for each label
    so its estimated text box doesn't overlap any label already placed. A
    fixed offset, or one chosen only by counting nearby points rather than
    checking actual text boxes, still piles labels on each other once 3+
    points sit close together in the same neighbourhood."""
    name_map = name_map or {}
    fig = ax.figure
    fig.canvas.draw()
    bbox_px = ax.get_window_extent()
    pt_per_px = 72.0 / fig.dpi
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    is_logx, is_logy = ax.get_xscale() == "log", ax.get_yscale() == "log"

    def data_to_pt(x, y):
        fx = ((np.log10(x) - np.log10(x0)) / (np.log10(x1) - np.log10(x0))) if is_logx else (x - x0) / (x1 - x0)
        fy = ((np.log10(y) - np.log10(y0)) / (np.log10(y1) - np.log10(y0))) if is_logy else (y - y0) / (y1 - y0)
        return (bbox_px.x0 + fx * bbox_px.width) * pt_per_px, (bbox_px.y0 + fy * bbox_px.height) * pt_per_px

    candidates = [(radius * np.cos(ang), radius * np.sin(ang))
                  for radius in (10, 18, 26, 34)
                  for ang in np.radians([45, -45, 135, -135, 0, 90, -90, 180])]

    def box_for(px, py, dx, dy, w, h):
        ha = "left" if dx >= 0 else "right"
        bx0 = px + dx if ha == "left" else px + dx - w
        by0 = py + dy - h / 2
        return ha, (bx0, by0, bx0 + w, by0 + h)

    placed_boxes = []
    for ax_, ay_, aha_, atext_ in avoid:
        a_fontsize = 8.5
        aw = max(len(line) for line in atext_.split("\n")) * a_fontsize * 0.54
        ah = atext_.count("\n") + 1
        ah = ah * a_fontsize * 1.4
        apx, apy = data_to_pt(ax_, ay_)
        placed_boxes.append(box_for(apx, apy, 0, 0, aw, ah)[1] if aha_ == "left"
                             else box_for(apx, apy, 0, 0, -aw, ah)[1])
    for _, r in rows.iterrows():
        x, y = r[x_col], max(r[y_col], 0.005)
        label = str(name_map.get(r[name_col], r[name_col]))
        px, py = data_to_pt(x, y)
        w, h = len(label) * fontsize * 0.54 + 3, fontsize * 1.25
        chosen = None
        for dx, dy in candidates:
            ha, box = box_for(px, py, dx, dy, w, h)
            if not any(box[2] > pb[0] and box[0] < pb[2] and box[3] > pb[1] and box[1] < pb[3]
                       for pb in placed_boxes):
                chosen = (dx, dy, ha, box)
                break
        if chosen is None:
            dx, dy = candidates[0]
            ha, box = box_for(px, py, dx, dy, w, h)
            chosen = (dx, dy, ha, box)
        dx, dy, ha, box = chosen
        ax.annotate(label, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                    fontsize=fontsize, fontweight="bold", color=INK, ha=ha, va="center", zorder=4)
        placed_boxes.append(box)


def hbar(counts, headline, desc, finding, fname, footnote, color=ACCENT, top=None, xlabel="studies", gradient=True):
    items = sorted(counts.items(), key=lambda kv: kv[1])
    if top:
        items = items[-top:]
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    # Headline/desc/finding text is placed at fixed axes-fraction offsets above
    # the axes (see set_headline), so charts with few bars need a taller floor
    # here or that header text collides with itself (and tight_layout can't
    # rescue it — the figure size, not just the padding, is too small).
    fig, ax = plt.subplots(figsize=(8, max(3.3, 0.38 * len(labels) + 1.8)))
    if gradient:
        # Use a power-scaled blue–teal gradient so very large outliers do not
        # force nearly all remaining bars into the same pale shade.
        norm = mcolors.PowerNorm(gamma=0.45, vmin=min(values), vmax=max(values))
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "blue_teal_count_gradient",
            ["#dcecf3", "#bddbe7", "#8fc7cf", "#5eb2ba", "#2f8f9d", "#1f5fa8"]
        )
        bar_colors = [cmap(norm(v)) for v in values]
    else:
        bar_colors = color
    ax.barh(labels, values, color=bar_colors, zorder=3)
    for y, v in enumerate(values):
        ax.text(v, y, f"  {v:,}", va="center", fontsize=9, color=INK)
    set_headline(ax, headline, desc, finding, fname)
    ax.set_xlabel(xlabel)
    clean_axes(ax)
    ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    set_footnote(fig, footnote)
    fig.tight_layout()
    fig.savefig(FIGS / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return labels[-1], values[-1]  # largest category, for headline text upstream


def pct(n, d):
    return round(100 * n / d, 1) if d else 0.0


def col_counts(colname):
    lv = LV[colname]
    c = Counter(studies[colname])
    return {lv[k]: v for k, v in c.items()}


def fig_entry(fname, title=None):
    headline, desc, finding = FIG_META[fname]
    return {"file": fname, "title": title or headline, "caption": f"{desc} {finding}"}


# Keyword rules mapping raw PubMed MeSH descriptor text to 11 broad disease
# categories modeled on HEE's MeSH C-tree groupings (used for
# fig_funder_opportunity.png). Deliberately excludes demographic/methods MeSH
# terms (Humans, Female, United States, Cross-Sectional Studies, ...) — those
# simply never match any category, which is correct: they aren't diseases.
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


def build_continuous_map_figure(fname, headline, desc, finding, footnote, iso3_list, z_list,
                                 cmap_stops, vmin, vmax, cbar_ticks, cbar_labels, cbar_title,
                                 landcolor="#e5e1d6"):
    """Composite helper for a single-value choropleth: renders the map tile
    via Plotly+kaleido, then draws a matplotlib colorbar built from the SAME
    colour stops (so the raster map and the vector colorbar always match
    exactly) plus the standard headline/footnote layout. Reused by
    fig_map_burden / fig_map_growth / fig_worldmap."""
    FIG_META[fname] = (headline, desc, finding)
    n = len(cmap_stops)
    colorscale = [[i / (n - 1), c] for i, c in enumerate(cmap_stops)]
    tmp = FIGS / f"_tmp_{fname}"
    fig_p = go.Figure(go.Choropleth(
        locations=iso3_list, locationmode="ISO-3", z=z_list, zmin=vmin, zmax=vmax,
        colorscale=colorscale, showscale=False, marker_line_color="white", marker_line_width=0.3))
    fig_p.update_geos(projection_type="robinson", showframe=False, showcoastlines=False,
                       landcolor=landcolor, bgcolor="rgba(0,0,0,0)", showcountries=False,
                       center=dict(lon=0, lat=0), projection_rotation=dict(lon=0, lat=0))
    fig_p.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", width=1600, height=800)
    fig_p.write_image(str(tmp), scale=2)

    cmap = mcolors.LinearSegmentedColormap.from_list(fname, cmap_stops)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    fig = plt.figure(figsize=(11, 8))
    ax_map = fig.add_axes([0.03, 0.10, 0.90, 0.62])
    ax_map.imshow(plt.imread(tmp))
    ax_map.axis("off")
    ax_map.set_facecolor(PAPER)

    cbar_ax = fig.add_axes([0.90, 0.20, 0.02, 0.36])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, cax=cbar_ax)
    cb.set_ticks(cbar_ticks)
    cb.set_ticklabels(cbar_labels)
    cb.ax.tick_params(labelsize=8)
    cb.outline.set_visible(False)
    fig.text(0.90, 0.60, cbar_title, fontsize=8, color=SUBHEAD_COLOR, ha="left", va="bottom")

    fig.text(0.02, 0.975, D(headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.925, D(desc), fontsize=9.5, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.875, D(finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    fig.text(0.01, 0.02, D(footnote), fontsize=7.6, color=SUBHEAD_COLOR, ha="left", va="bottom", wrap=True)
    fig.patch.set_facecolor(PAPER)
    fig.savefig(FIGS / fname, dpi=150)
    plt.close(fig)
    tmp.unlink(missing_ok=True)


def render_discrete_map_png(iso3_list, codes, palette, tmp_path, landcolor="#e5e1d6", width=1600, height=800):
    """Renders a discrete-category Robinson choropleth to a PNG via Plotly +
    kaleido, for compositing into a matplotlib figure with imshow(). Kept
    separate from matplotlib so every figure's headline/footnote typography
    stays in one place (set_headline/set_footnote) — Plotly here is only a
    map-tile renderer, not the source of the chart's text or branding.
    `codes` are ints in [0, len(palette)); countries not in `iso3_list` fall
    back to `landcolor` (e.g. no data)."""
    n = len(palette)
    colorscale = []
    for i, color in enumerate(palette):
        colorscale.append([i / n, color])
        colorscale.append([(i + 1) / n, color])
    fig = go.Figure(go.Choropleth(
        locations=iso3_list, locationmode="ISO-3",
        z=[c + 0.5 for c in codes], zmin=0, zmax=n,
        colorscale=colorscale, showscale=False,
        marker_line_color="white", marker_line_width=0.3,
    ))
    fig.update_geos(projection_type="robinson", showframe=False, showcoastlines=False,
                     landcolor=landcolor, bgcolor="rgba(0,0,0,0)", showcountries=False,
                     center=dict(lon=0, lat=0), projection_rotation=dict(lon=0, lat=0))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)", width=width, height=height)
    fig.write_image(str(tmp_path), scale=2)


def _sq_worst_ratio(row, side):
    s = sum(row)
    if s == 0 or not row:
        return float("inf")
    return max((side * side * max(row)) / (s * s), (s * s) / (side * side * min(row)))


def _sq_layout_row(row, x, y, w, h, horizontal):
    s = sum(row)
    rects = []
    if horizontal:
        rh = s / w
        cx = x
        for v in row:
            rw = v / rh if rh > 0 else 0
            rects.append((cx, y, rw, rh))
            cx += rw
        return rects, (x, y + rh, w, h - rh)
    rw = s / h
    cy = y
    for v in row:
        rh2 = v / rw if rw > 0 else 0
        rects.append((x, cy, rw, rh2))
        cy += rh2
    return rects, (x + rw, y, w - rw, h)


def squarify_treemap(values, x, y, w, h):
    """Squarified treemap (Bruls/Huizing/van Wijk). `values` must already sum
    to w*h. Returns rects in the SAME order as `values`."""
    order = sorted(range(len(values)), key=lambda i: -values[i])
    sizes = [values[i] for i in order]
    result = [None] * len(values)
    row, idx = [], 0
    cx, cy, cw, ch = x, y, w, h
    while idx < len(sizes):
        c = sizes[idx]
        side = min(cw, ch)
        if not row or _sq_worst_ratio(row, side) >= _sq_worst_ratio(row + [c], side):
            row.append(c)
            idx += 1
        else:
            rects, (cx, cy, cw, ch) = _sq_layout_row(row, cx, cy, cw, ch, cw >= ch)
            row_start = idx - len(row)
            for k, r in enumerate(rects):
                result[order[row_start + k]] = r
            row = []
    if row:
        rects, _ = _sq_layout_row(row, cx, cy, cw, ch, cw >= ch)
        row_start = idx - len(row)
        for k, r in enumerate(rects):
            result[order[row_start + k]] = r
    return result


def squarify_treemap_balanced(values, x, y, w, h):
    """A balanced squarified treemap layout for editorial card-style figures.
    Unlike the legacy helper above, each row is laid along the rectangle's
    shorter side, which avoids very thin strip tiles for smaller categories.
    `values` must already sum to w*h. Returns rects in input order.
    """
    order = sorted(range(len(values)), key=lambda i: -values[i])
    sizes = [values[i] for i in order]
    result = [None] * len(values)
    row, idx = [], 0
    cx, cy, cw, ch = x, y, w, h
    while idx < len(sizes):
        c = sizes[idx]
        side = min(cw, ch)
        if not row or _sq_worst_ratio(row, side) >= _sq_worst_ratio(row + [c], side):
            row.append(c)
            idx += 1
        else:
            # If the remaining rectangle is wide, lay the row as a vertical
            # column along its shorter side; if tall, lay it horizontally.
            rects, (cx, cy, cw, ch) = _sq_layout_row(row, cx, cy, cw, ch, cw < ch)
            row_start = idx - len(row)
            for k, r in enumerate(rects):
                result[order[row_start + k]] = r
            row = []
    if row:
        rects, _ = _sq_layout_row(row, cx, cy, cw, ch, cw < ch)
        row_start = idx - len(row)
        for k, r in enumerate(rects):
            result[order[row_start + k]] = r
    return result


def irls_logit(X, y, n_iter=50, tol=1e-8):
    """Plain iteratively-reweighted-least-squares logistic regression (no
    statsmodels dependency). Returns (coefficients, covariance matrix) so
    Wald 95% CIs can be built for a forest plot — sklearn's LogisticRegression
    gives point estimates only, not standard errors."""
    n, p = X.shape
    beta = np.zeros(p)
    for _ in range(n_iter):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-eta))
        w = np.clip(mu * (1 - mu), 1e-8, None)
        H = (X.T * w) @ X
        grad = X.T @ (y - mu)
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, grad, rcond=None)[0]
        beta_new = beta + step
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new
    eta = X @ beta
    mu = 1 / (1 + np.exp(-eta))
    w = np.clip(mu * (1 - mu), 1e-8, None)
    H = (X.T * w) @ X
    # Some filtered panels can make the design matrix rank-deficient (for
    # example, when an income-group dummy has no variation). In that case a
    # direct inverse does not exist. Fall back to the Moore-Penrose
    # pseudoinverse so the figure-generation run can continue without changing
    # the underlying model specification.
    try:
        cov = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(H)
    return beta, cov


def classify_disease(mesh_theme):
    """Assigns a study's semicolon-separated MeSH term list to whichever of the
    11 disease categories has the most matching terms (each term counts toward
    its first-matching category only). Returns None if no term matches."""
    terms = [t.strip(" *").lower() for t in mesh_theme.split(";") if t.strip(" *")]
    scores = Counter()
    for term in terms:
        for cat, kws in MESH_DISEASE_KEYWORDS:
            if any(kw in term for kw in kws):
                scores[cat] += 1
                break
    return scores.most_common(1)[0][0] if scores else None



# ---------------------------------------------------------------------------
# 11c-authors. Author affiliation data (v2 extraction). author_affiliation_
# countries is harvested as a semicolon-separated, deduplicated set of ISO2
# codes per study (not one-per-author) — mapped to ISO3 via ISO2_TO_ISO3 and
# reused by the forest plot below, fig_map_authorship, fig_collab_chord and
# fig_funder_capacity. research_funder is loaded here too for fig_funder_funders.
# ---------------------------------------------------------------------------
raw_csv_available = RAW_CSV.exists()
author_countries_of_s = {}
funder_of_s = {}

# Accept the common formats seen in exports: ISO2 (US), ISO3 (USA), Python/list-like
# strings (['US', 'GB']), and semicolon-separated country names. This avoids treating
# the mere presence of the raw CSV as proof that authorship data parsed successfully.
iso3_set = {r["iso3"] for r in countries if r.get("iso3")}
country_name_to_iso3 = {
    re.sub(r"[^a-z0-9]+", " ", r["country"].lower()).strip(): r["iso3"]
    for r in countries if r.get("country") and r.get("iso3")
}
country_name_to_iso3.update({
    "united states": "USA",
    "usa": "USA",
    "uk": "GBR",
    "united kingdom": "GBR",
    "south korea": "KOR",
    "korea republic of": "KOR",
    "russia": "RUS",
    "tanzania": "TZA",
    "democratic republic of the congo": "COD",
    "dr congo": "COD",
})


def _parse_author_country_value(value):
    if not isinstance(value, str) or not value.strip() or value.strip().lower() == "could not find":
        return set()
    s = value.strip()
    found = set()

    # Codes embedded in ordinary, list-like, or delimited strings.
    for tok in re.findall(r"\b[A-Za-z]{2,3}\b", s):
        up = tok.upper()
        if up in ISO2_TO_ISO3:
            found.add(ISO2_TO_ISO3[up])
        elif up in iso3_set:
            found.add(up)

    # Full country-name entries, normally separated by semicolon / pipe / slash.
    cleaned = re.sub(r"[\[\]{}()'\"]", "", s)
    for part in re.split(r"[;|/]", cleaned):
        key = re.sub(r"[^a-z0-9]+", " ", part.lower()).strip()
        if key in country_name_to_iso3:
            found.add(country_name_to_iso3[key])

    return found


if raw_csv_available:
    auth_raw = pd.read_csv(RAW_CSV, usecols=["record_id", "author_affiliation_countries", "research_funder"])
    auth_raw = auth_raw[auth_raw["record_id"].isin(ID_TO_IDX)].copy()
    auth_raw["idx"] = auth_raw["record_id"].map(ID_TO_IDX)
    for idx, ac, fn in zip(auth_raw["idx"], auth_raw["author_affiliation_countries"], auth_raw["research_funder"]):
        iso3s = _parse_author_country_value(ac)
        if iso3s:
            author_countries_of_s[idx] = iso3s
        if isinstance(fn, str) and fn.strip() and fn != "Could not find":
            funder_of_s[idx] = fn

have_authors = bool(author_countries_of_s)
have_funders = bool(funder_of_s)
print(f"Authorship parse: {len(author_countries_of_s):,} studies with recognised affiliation countries; "
      f"funder parse: {len(funder_of_s):,} studies with a research funder.")
if raw_csv_available and not have_authors:
    print("WARNING: raw CSV exists, but no author affiliation countries could be parsed; authorship-only figures will be skipped.")

iso3_of_c = {i: r["iso3"] for i, r in enumerate(countries)}
income_by_iso3 = {r["iso3"]: r["income"] for r in countries}

# --- fig_funder_funders: top research funders, name-normalized ---
# A study can list >1 funder (3,846 of 10,262 funded studies do); each is counted once
# per study it funds, in every funder's bucket it names — the same "one study can land in
# several buckets" convention used throughout this project for other multi-valued fields.
if have_funders:
    funder_raw_counts_by_key = defaultdict(Counter)
    funder_study_counts = Counter()
    funders_of_s = {}  # study idx -> set of normalized funder keys; reused by the funder x
                        # function / trend / alluvial figures below
    for s, fn in funder_of_s.items():
        toks = {t.strip() for t in fn.split(";") if t.strip()}
        keys_this_study = set()
        for t in toks:
            key = _norm_funder_key(t)
            if key in FUNDER_ALIASES:
                key = _norm_funder_key(FUNDER_ALIASES[key])
            funder_raw_counts_by_key[key][t] += 1
            keys_this_study.add(key)
        for key in keys_this_study:
            funder_study_counts[key] += 1
        funders_of_s[s] = keys_this_study

    funder_display_name = {key: ctr.most_common(1)[0][0] for key, ctr in funder_raw_counts_by_key.items()}
    for alias_to in FUNDER_ALIASES.values():
        funder_display_name[_norm_funder_key(alias_to)] = alias_to

    funder_counts = {funder_display_name[key]: n for key, n in funder_study_counts.items()}
    n_funded = len(funder_of_s)
    top_funder_name, top_funder_n = max(funder_counts.items(), key=lambda kv: kv[1])
    # Restore the original ranked bar figure as the main output and save the treemap
    # as an additional option, rather than replacing one with the other.
    top_funders = sorted(funder_counts.items(), key=lambda kv: -kv[1])[:15]

    # -------------------------------------------------------------------------
    # --- fig_wellcome_priorities: evidence and funders across Wellcome themes ---
    # These are independent flags rather than a partition: one study may address
    # several priority themes. The rules deliberately reuse existing metadata.
    priority_raw = pd.read_csv(
        RAW_CSV,
        usecols=["record_id", "mesh_theme", "ml_topics"],
    )
    priority_raw = priority_raw[priority_raw["record_id"].isin(ID_TO_IDX)]
    infectious_keywords = MESH_DISEASE_KEYWORDS[0][1]
    mental_keywords = [
        "mental disorder", "mental health", "depress", "anxiety disorder",
        "schizophrenia", "bipolar disorder", "substance-related disorder",
        "substance abuse", "psychiatric", "autis", "attention deficit",
    ]
    climate_mesh_keywords = [
        "climate change", "global warming", "extreme heat", "heat stress",
        "hot temperature", "heatwave",
    ]
    priority_order = ["Infectious Diseases", "Mental Health", "Climate & Health"]
    priority_colors = {
        "Infectious Diseases": "#2f6fb0",
        "Mental Health": "#2a9d8f",
        "Climate & Health": "#67a65b",
    }
    priorities_of_s = {}
    for row in priority_raw.itertuples(index=False):
        mesh_text = str(row.mesh_theme).lower() if pd.notna(row.mesh_theme) else ""
        topic_text = str(row.ml_topics).lower() if pd.notna(row.ml_topics) else ""
        tags = set()
        if any(keyword in mesh_text for keyword in infectious_keywords):
            tags.add("Infectious Diseases")
        if any(keyword in mesh_text for keyword in mental_keywords):
            tags.add("Mental Health")
        if (any(keyword in mesh_text for keyword in climate_mesh_keywords)
                or "climate change and health impacts" in topic_text):
            tags.add("Climate & Health")
        if tags:
            priorities_of_s[ID_TO_IDX[row.record_id]] = tags

    priority_counts = Counter(
        theme for themes in priorities_of_s.values() for theme in themes
    )
    donor_priority_counts = defaultdict(Counter)
    for study_idx, themes in priorities_of_s.items():
        for funder_key in funders_of_s.get(study_idx, set()):
            donor = funder_display_name[funder_key]
            for theme in themes:
                donor_priority_counts[donor][theme] += 1

    top_priority_donors = [name for name, _ in top_funders[:12]]
    priority_matrix = np.array([
        [donor_priority_counts[donor][theme] for theme in priority_order]
        for donor in top_priority_donors
    ])
    leading_theme = max(priority_order, key=lambda theme: priority_counts[theme])
    leading_donor = (max(top_priority_donors,
                         key=lambda donor: sum(donor_priority_counts[donor].values()))
                     if top_priority_donors else "No named funder")
    # Panel C: financing functions coded on the studies matched to each theme.
    # A study coded to several functions counts once per function; shares use
    # the theme's matched-study count as denominator. "Unclear" is excluded.
    funcs_of_priority_s = defaultdict(set)
    for s, g in zip(function_j["s"], function_j["g"]):
        if s in priorities_of_s and FUNC_GRPS[g] != "Unclear":
            funcs_of_priority_s[s].add(FUNC_GRPS[g])
    theme_func_counts = defaultdict(Counter)
    for study_idx, themes in priorities_of_s.items():
        for fn in funcs_of_priority_s.get(study_idx, set()):
            for theme in themes:
                theme_func_counts[theme][fn] += 1
    func_totals = Counter()
    for theme in priority_order:
        func_totals.update(theme_func_counts[theme])
    priority_funcs = [fn for fn, _ in func_totals.most_common() if fn != "Other"]
    if "Other" in func_totals:
        priority_funcs.append("Other")
    func_count_matrix = np.array([
        [theme_func_counts[theme][fn] for theme in priority_order] for fn in priority_funcs
    ])
    func_share_matrix = np.array([
        [100 * theme_func_counts[theme][fn] / priority_counts[theme] if priority_counts[theme] else 0
         for theme in priority_order] for fn in priority_funcs
    ])
    top_func_by_theme = {
        theme: max(priority_funcs, key=lambda fn: theme_func_counts[theme][fn])
        for theme in priority_order if priority_funcs
    }

    priority_desc = (
        "Panel A shows studies classified to each Wellcome priority theme; Panel B shows the top "
        "funders of those studies by theme; Panel C shows the financing functions those studies "
        "were coded to. Categories are not mutually exclusive."
    )
    priority_finding = (
        f"{leading_theme} has the largest evidence base ({priority_counts[leading_theme]:,} studies); "
        f"{leading_donor} funds the largest number of priority-theme study links; "
        f"{top_func_by_theme.get(leading_theme, 'n/a')} is the most common financing function "
        f"in {leading_theme} studies."
    )
    FIG_META["fig_wellcome_priorities.png"] = (
        "Indicative mapping of studies to Wellcome priority themes",
        priority_desc,
        priority_finding,
    )

    # Layout: A (top-left) and C (bottom-left) stacked; B spans the right column.
    fig = plt.figure(figsize=(15.2, 13.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1.25], height_ratios=[0.42, 1],
                          wspace=0.62, hspace=0.42)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_b = fig.add_subplot(gs[:, 1])
    fig.suptitle("Indicative mapping of studies to Wellcome priority themes", x=0.055, y=0.975,
                 ha="left", fontsize=19, fontweight="bold", color=INK)
    fig.text(0.055, 0.94, "\n".join(textwrap.wrap(priority_desc, 150)), ha="left", va="top",
             fontsize=10.5, color=SUBHEAD_COLOR)
    fig.text(0.055, 0.903, "\n".join(textwrap.wrap(priority_finding, 140)), ha="left", va="top",
             fontsize=11, fontweight="bold", color=INK)

    bar_values = [priority_counts[theme] for theme in priority_order]
    bar_y = np.arange(len(priority_order))
    ax_a.barh(bar_y, bar_values, color=[priority_colors[t] for t in priority_order],
              height=0.58, zorder=3)
    ax_a.set_yticks(bar_y, priority_order)
    ax_a.invert_yaxis()
    ax_a.set_xlabel(f"studies (share of all {N:,} studies)")
    ax_a.set_title("Panel A - How much evidence addresses\nWellcome priority themes?",
                   loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=14)
    for y, value in zip(bar_y, bar_values):
        ax_a.text(value, y, f"  {value:,}  ({100 * value / N:.1f}% of all studies)",
                  va="center", ha="left", fontsize=9.5, fontweight="bold", color=INK)
    ax_a.set_xlim(0, max(bar_values) * 1.42 if bar_values else 1)
    clean_axes(ax_a)
    ax_a.grid(axis="y", visible=False)

    vmax = max(int(priority_matrix.max()), 1) if priority_matrix.size else 1
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "priority_funding", ["#f3f7f5", "#b7d9ce", "#25835f", "#114c3d"]
    )
    image = ax_b.imshow(priority_matrix, aspect="auto", cmap=cmap, vmin=0, vmax=vmax)
    ax_b.set_xticks(np.arange(len(priority_order)), priority_order)
    ax_b.set_yticks(
        np.arange(len(top_priority_donors)),
        ["\n".join(textwrap.wrap(name, width=28, break_long_words=False))
         for name in top_priority_donors],
    )
    ax_b.set_title("Panel B - Which donors fund research\nin each priority theme?",
                   loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=14)
    ax_b.tick_params(axis="x", rotation=0, labelsize=9)
    ax_b.tick_params(axis="y", labelsize=8.5, length=0)
    for row_idx in range(priority_matrix.shape[0]):
        for col_idx in range(priority_matrix.shape[1]):
            value = int(priority_matrix[row_idx, col_idx])
            ax_b.text(col_idx, row_idx, f"{value:,}", ha="center", va="center",
                      fontsize=8.5, fontweight="bold",
                      color="white" if value > vmax * 0.55 else INK)
    for spine in ax_b.spines.values():
        spine.set_visible(False)
    colorbar = fig.colorbar(image, ax=ax_b, fraction=0.035, pad=0.025)
    colorbar.set_label("funded studies", fontsize=9, color=SUBHEAD_COLOR)
    colorbar.ax.tick_params(labelsize=8)
    colorbar.outline.set_visible(False)

    # Panel C: colour = share of the theme's studies, so themes of very
    # different size compare fairly; labels give count and share.
    func_cmap = mcolors.LinearSegmentedColormap.from_list(
        "priority_function", ["#f4f7fb", "#bcd3ea", "#3f7fc0", "#173f73"]
    )
    share_max = max(float(func_share_matrix.max()), 1.0) if func_share_matrix.size else 1.0
    image_c = ax_c.imshow(func_share_matrix, aspect="auto", cmap=func_cmap, vmin=0, vmax=share_max)
    ax_c.set_xticks(np.arange(len(priority_order)), priority_order)
    ax_c.set_yticks(
        np.arange(len(priority_funcs)),
        ["\n".join(textwrap.wrap(SHORT_FN.get(fn, fn), width=26, break_long_words=False))
         for fn in priority_funcs],
    )
    ax_c.set_title("Panel C - Which financing functions do\nthese studies address?",
                   loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=14)
    ax_c.tick_params(axis="x", rotation=0, labelsize=9)
    ax_c.tick_params(axis="y", labelsize=8.5, length=0)
    for row_idx in range(func_count_matrix.shape[0]):
        for col_idx in range(func_count_matrix.shape[1]):
            count = int(func_count_matrix[row_idx, col_idx])
            share = func_share_matrix[row_idx, col_idx]
            share_txt = "<1%" if 0 < share < 1 else f"{share:.0f}%"
            ax_c.text(col_idx, row_idx, f"{count:,}\n{share_txt}", ha="center", va="center",
                      fontsize=8, fontweight="bold", linespacing=1.1,
                      color="white" if share > share_max * 0.55 else INK)
    for spine in ax_c.spines.values():
        spine.set_visible(False)
    colorbar_c = fig.colorbar(image_c, ax=ax_c, fraction=0.045, pad=0.03)
    colorbar_c.set_label("% of the theme's studies", fontsize=9, color=SUBHEAD_COLOR)
    colorbar_c.ax.tick_params(labelsize=8)
    colorbar_c.outline.set_visible(False)

    fig.text(
        0.055, 0.012,
        "\n".join(textwrap.wrap(
            f"Base and Panel A percentage denominator: all {N:,} studies in the evidence map. Themes are "
            "independent flags and may overlap. Infectious Diseases and "
            "Mental Health use explicit disease/mental-health terms in existing MeSH-derived metadata; Climate "
            "& Health uses explicit climate/heat MeSH terms or the OpenAlex topic 'Climate Change and Health "
            "Impacts'. Panel B disaggregates the top 12 normalized funders overall; a multi-funder study "
            "counts once for each named funder. Panel C counts studies matched to each theme by their coded "
            "health financing function; a study coded to several functions counts once per function, so "
            "column shares can exceed 100%. Shares use the theme's matched studies as denominator; "
            "'Unclear' function codes are excluded.", 190)),
        ha="left", va="bottom", fontsize=8.2, color=SUBHEAD_COLOR,
    )
    fig.subplots_adjust(left=0.13, right=0.97, top=0.80, bottom=0.1)
    fig.savefig(FIGS / "fig_wellcome_priorities.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

# ---------------------------------------------------------------------------
# 5-8. Study design / type of analysis / data type / data source - the original
# separate bar charts, replaced on the site by fig_methods_characteristics.png
# ---------------------------------------------------------------------------
top_design2, second_design = sorted(col_counts("study_design").items(), key=lambda kv: -kv[1])[:2]
top_design, top_design_n = top_design2
hbar(col_counts("study_design"), "Cross-sectional analysis dominates study design",
     "Study design of the analysis population.",
     f"{top_design} leads at {top_design_n:,} studies, well ahead of {second_design[0]}'s {second_design[1]:,}.",
     "fig_design_bar.png", f"Base: {N:,} studies (analysis population).")

pct_quant = dict_json["meta"]["pct_quant"]
hbar(col_counts("type_of_analysis"), "Most studies are quantitative",
     "Type of analysis, deduced from the abstract text.",
     f"{pct_quant}% of studies use a quantitative analysis — qualitative and mixed-methods work "
     f"together make up the remaining {round(100 - pct_quant, 1)}%.",
     "fig_analysis_bar.png", f"Base: {N:,} studies (analysis population).", color=GOLD)

top_dt2, second_dt = sorted(col_counts("data_type").items(), key=lambda kv: -kv[1])[:2]
top_datatype, top_datatype_n = top_dt2
hbar(col_counts("data_type"), "Cross-sectional data is the norm",
     "Data type used by the analysis population.",
     f"{top_datatype} leads at {top_datatype_n:,} studies, ahead of {second_dt[0]}'s {second_dt[1]:,}.",
     "fig_datatype_bar.png", f"Base: {N:,} studies (analysis population).")

top_dsr2, second_dsr = sorted(col_counts("data_source").items(), key=lambda kv: -kv[1])[:2]
top_datasource, top_datasource_n = top_dsr2
hbar(col_counts("data_source"), "Administrative records are the leading data source",
     "Data source used by the analysis population.",
     f"{top_datasource} leads at {top_datasource_n:,} studies, ahead of {second_dsr[0]}'s {second_dsr[1]:,}.",
     "fig_datasource_bar.png", f"Base: {N:,} studies (analysis population).", color=GOLD)

# ---------------------------------------------------------------------------
# 12. Pipeline funnel
# ---------------------------------------------------------------------------
content = load("content.json")
funnel_raw = content["funnel"]


def num(s):
    return int(s.replace(",", ""))


stages = []
for row in funnel_raw:
    lbl = row["label"]
    if "Stage 0 input" in lbl:
        stages.append(("Records in the v5 file", num(row["records"])))
    elif "With a financing-function tag" in lbl:
        stages.append(("Financing-function tag", num(row["records"])))
    elif "DOI recovered" in lbl and "No DOI" not in lbl:
        stages.append(("DOI recovered", num(row["records"])))

mesh_pubmed = next(num(r["records"]) for r in funnel_raw if "PubMed MeSH" in r["label"])
mesh_fallback = next(num(r["records"]) for r in funnel_raw if "OpenAlex fallback" in r["label"])
stages.append(("MeSH/topic theme found", mesh_pubmed + mesh_fallback))
n_ff_tag = next(v for k, v in stages if k == "Financing-function tag")
n_doi = next(v for k, v in stages if k == "DOI recovered")

labels = [s[0] for s in stages]
values = [s[1] for s in stages]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.barh(labels[::-1], values[::-1], color=ACCENT, zorder=3)
for y, v in enumerate(values[::-1]):
    ax.text(v, y, f"  {v:,}", va="center", fontsize=9, color=INK)
set_headline(ax, "Nearly every v5 record carries a financing-function tag",
             "Record counts in the v5 file, from classification to DOI and topic-theme recovery.",
             f"{pct(n_ff_tag, N)}% of {N:,} records have a financing-function tag; {pct(n_doi, N)}% have a DOI "
             f"and {pct(mesh_pubmed + mesh_fallback, N)}% a MeSH or topic theme.",
             "fig_funnel.png")
ax.set_xlabel("records")
clean_axes(ax)
ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
set_footnote(fig, f"Base: {SOURCE_NAME}, counted from the file itself (there is no v5 stage-funnel workbook). "
                   "See the Methods tab for the\nstage-by-stage breakdown.")
fig.tight_layout()
fig.savefig(FIGS / "fig_funnel.png", dpi=150, bbox_inches="tight")
plt.close(fig)

print("Built hidden figures: fig_wellcome_priorities.png "
      + ("" if have_funders else "(skipped: no funder data) ") + "fig_funnel.png and the four Methods & data bar charts")
