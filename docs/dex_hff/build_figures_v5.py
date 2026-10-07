"""Generates docs/figures/*.png for the HFF Gallery tab from the already-built
docs/data/*.json (no dependency on the raw 336MB CSV, which isn't committed).

Matches HEE's editorial convention exactly (checked against HEE's own .webp
figures): a bold HEADLINE states the claim; below it, a plain DESCRIPTION line
says what the chart shows, followed by a **bold FINDING sentence** with the
actual numbers/comparison. The same three pieces are reused verbatim as the
Gallery card's title/caption in content.json (via FIG_META) — one source of
truth per figure. 

Run: python docs/dex_hff/build_figures.py
"""
import json
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

ROOT = Path(__file__).resolve().parent.parent  # docs/
DATA = ROOT / "data"
FIGS = ROOT / "figures"
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
# 1. Growth: cumulative studies over time, vs. an early-rate reference line
#    (flagship treatment — mirrors HEE's fig_growth.webp)
# ---------------------------------------------------------------------------
year_counts = Counter(studies["year"])
years = sorted(year_counts)
full_years = [y for y in years if y != 2026]
cum = []
running = 0
for y in years:
    running += year_counts[y]
    cum.append(running)
total_full = sum(year_counts[y] for y in full_years)
half_year = next(y for y, c in zip(years, cum) if c >= total_full / 2)

# Reference: if the 2010-2012 average annual rate had continued for every year.
early_rate = sum(year_counts[y] for y in years[:3]) / 3
ref_line = [early_rate * (i + 1) for i in range(len(years))]

fig, ax = plt.subplots(figsize=(8.5, 5))
ax.fill_between(years, cum, color=ACCENT, alpha=0.15, zorder=1)
ax.plot(years, cum, color=ACCENT, linewidth=2.75, zorder=3)
ax.plot(years, ref_line, color=SUBHEAD_COLOR, linewidth=1.4, linestyle=(0, (4, 3)), zorder=2)
ax.text(years[int(len(years) * 0.55)], ref_line[int(len(years) * 0.55)],
        "if annual output had\nstayed at its 2010–12 rate", color=SUBHEAD_COLOR, fontsize=8.5,
        rotation=18, ha="left", va="bottom")
ax.axvline(half_year, color="#8a8272", linewidth=0.9, linestyle=":", zorder=2)
ax.annotate(f"half of all {total_full:,} full-year records\npublished {half_year} or later",
            xy=(half_year, total_full * 0.5), xytext=(half_year - 0.3, total_full * 0.62),
            fontsize=9.5, fontweight="bold", color=INK, ha="right")
ax.plot([years[-1]], [cum[-1]], marker="o", color=ACCENT, markersize=6, zorder=4)
ax.annotate(f"{years[-1]}\n(partial)", xy=(years[-1], cum[-1]), xytext=(-4, 8),
            textcoords="offset points", fontsize=9, color=INK, ha="right")
set_headline(ax, "Publications growing faster than linearly",
             "Cumulative records analysed by publication year.",
             f"Volume grew {round(cum[-1] / max(cum[0], 1), 1)}× since {years[0]} — half of all "
             f"{total_full:,} records were published {half_year} or later.",
             "fig_growth.png")
ax.set_ylabel("cumulative records")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=9))
ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
ax.set_ylim(0, cum[-1] * 1.18)
clean_axes(ax)
ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
set_footnote(fig, f"Base: {total_full:,} records by publication year between {years[0]}–{full_years[-1]}. "
                   f"{years[-1]} data covers only part of the year. Reference: cumulative growth at the {years[0]}–{years[2]} average annual rate.")
fig.tight_layout()
fig.savefig(FIGS / "fig_growth.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 2. Financing function counts, vs. an equal-share reference line
#    (flagship treatment)
# ---------------------------------------------------------------------------
func_counts = Counter()
for g in function_j["g"]:
    func_counts[FUNC_GRPS[g]] += 1
top_func, top_func_n = func_counts.most_common(1)[0]
_, (second_func, second_func_n) = func_counts.most_common(2)
mean_func = sum(func_counts.values()) / len(func_counts)

items = sorted(func_counts.items(), key=lambda kv: kv[1])
flabels, fvalues = [k for k, _ in items], [v for _, v in items]
flabels_wrapped = ["\n".join(textwrap.wrap(lbl, width=42, break_long_words=False)) for lbl in flabels]
fig, ax = plt.subplots(figsize=(13.2, 7.2))
func_norm = mcolors.PowerNorm(gamma=0.58, vmin=min(fvalues), vmax=max(fvalues))
func_cmap = mcolors.LinearSegmentedColormap.from_list(
    "financing_function_gradient",
    ["#d9edf0", "#9fd3d4", "#58b8b3", "#258f91", "#2f79b9", "#1f5fa8"],
)
bar_colors = [func_cmap(func_norm(value)) for value in fvalues]
ax.barh(flabels_wrapped, fvalues, color=bar_colors, zorder=3)
xmax = max(fvalues) * 1.14
ax.set_xlim(0, xmax)
value_pad = max(fvalues) * 0.012
for y, v in enumerate(fvalues):
    ax.text(v + value_pad, y, f"{v:,}", va="center", fontsize=9.5, color=INK)
ax.axvline(mean_func, color=SUBHEAD_COLOR, linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
ax.annotate(f"average across {len(func_counts)} functions: {mean_func:,.0f}",
            xy=(mean_func, 0.4), xytext=(mean_func + max(fvalues) * 0.02, 0.4),
            fontsize=9, color=SUBHEAD_COLOR, ha="left", va="bottom")
n_above = sum(1 for v in fvalues if v >= mean_func)
set_headline(ax, f"{n_above} of {len(func_counts)} financing functions punch above the per-function average",
             "Studies by financing function — a study can carry more than one.",
             f"{top_func} leads at {top_func_n:,} studies, {round(top_func_n / second_func_n, 1)}× "
             f"{second_func}'s {second_func_n:,}; capital-investment financing trails furthest behind.",
             "fig_function_bar.png")
ax.set_xlabel("studies")
ax.tick_params(axis="y", labelsize=10.5)
clean_axes(ax)
ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
set_footnote(fig, f"Base: {sum(func_counts.values()):,} financing-function tags across {N:,} studies "
                   f"(a study can carry more than one tag).")
fig.subplots_adjust(left=0.31, right=0.96, top=0.78, bottom=0.14)
fig.savefig(FIGS / "fig_function_bar.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 3. Financing function composition over time (top 5, share of tagged studies)
# ---------------------------------------------------------------------------
top5 = [k for k, _ in func_counts.most_common(5)]
year_of_study = studies["year"]
by_year_func = defaultdict(lambda: defaultdict(int))
totals_by_year = defaultdict(int)
seen = set()
for s, g in zip(function_j["s"], function_j["g"]):
    name = FUNC_GRPS[g]
    y = year_of_study[s]
    if name in top5:
        by_year_func[y][name] += 1
    key = (s, y)
    if key not in seen:
        seen.add(key)
        totals_by_year[y] += 1
years2 = sorted(by_year_func)
top_func_share_first = 100 * by_year_func[years2[0]].get(top_func, 0) / max(totals_by_year[years2[0]], 1)
top_func_share_last = 100 * by_year_func[years2[-2] if years2[-1] == 2026 else years2[-1]].get(top_func, 0) / \
    max(totals_by_year[years2[-2] if years2[-1] == 2026 else years2[-1]], 1)
fig, ax = plt.subplots(figsize=(9, 5.2))
palette = [FUNCTION_COLORS.get(name, "#8FA6B8") for name in top5]
bottom = [0] * len(years2)
for name, col in zip(top5, palette):
    vals = [100 * by_year_func[y].get(name, 0) / max(totals_by_year[y], 1) for y in years2]
    ax.bar(years2, vals, bottom=bottom, label=name, color=col, zorder=3, width=0.75)
    bottom = [b + v for b, v in zip(bottom, vals)]
set_headline(ax, "The financing-function mix has stayed fairly stable since 2010",
             "Share of tagged studies by year, top 5 functions; a study can carry more than one, so bars exceed 100%.",
             f"{top_func}'s share moved only from {top_func_share_first:.0f}% to {top_func_share_last:.0f}% "
             f"across the whole period — no function's relative weight shifted sharply.",
             "fig_function_time.png")
ax.set_ylabel("share of tagged studies (%)")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=9))
clean_axes(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=9)
set_footnote(fig, f"Base: {sum(totals_by_year.values()):,} function tags among the top 5 functions, by publication year.")
fig.tight_layout()
fig.savefig(FIGS / "fig_function_time.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 3a-alt. Alternative view of the same top-5 financing-function composition:
# reference-style line chart with clear right-side labels and a cool modern palette.
share_by_func = {name: [100 * by_year_func[y].get(name, 0) / max(totals_by_year[y], 1) for y in years2]
                 for name in top5}
fig, ax = plt.subplots(figsize=(12.8, 5.1))
line_palette = [FUNCTION_COLORS.get(name, "#8FA6B8") for name in top5]
label_map = {
    "Benefits decisions": "Benefits decisions",
    "Public financial management": "Public financial\nmanagement",
    "Purchasing": "Purchasing",
    "Revenue Raising": "Revenue raising",
    "Revenue raising": "Revenue raising",
    "Pooling": "Pooling",
}
for name, col in zip(top5, line_palette):
    vals = share_by_func[name]
    ax.plot(years2, vals, color=col, linewidth=2.6, marker="o", markersize=6.2,
            markerfacecolor=col, markeredgecolor=col, zorder=3, solid_capstyle="round")

# Reference-style labels on the right. Label positions are collision-adjusted in
# data coordinates, so they stay readable even if two series finish close together.
end_vals = {name: share_by_func[name][-1] for name in top5}
ordered_names = sorted(top5, key=lambda n: end_vals[n])
min_label_gap = 3.0
label_y = {}
prev_y = None
for name in ordered_names:
    y = end_vals[name]
    if prev_y is not None and y < prev_y + min_label_gap:
        y = prev_y + min_label_gap
    label_y[name] = y
    prev_y = y
label_x = max(years2) + 3.8
for name, col in zip(top5, line_palette):
    ylab = label_y[name]
    ax.plot([label_x - 0.9, label_x - 0.25], [ylab, ylab], color=col,
            linewidth=2.6, solid_capstyle="round", clip_on=False, zorder=3)
    ax.plot([label_x - 0.58], [ylab], marker="o", color=col, markersize=7,
            clip_on=False, zorder=4)
    ax.text(label_x, ylab, label_map.get(name, name), color=col,
            fontsize=12.0, fontweight="medium", va="center", ha="left",
            linespacing=1.08, clip_on=False)

set_headline(ax, "A line-chart view shows the same stable financing-function mix",
             "Share of tagged studies by year, top 5 functions, shown as separate lines; a study can carry more than one, so totals can exceed 100%.",
             f"{top_func}'s share moved only from {top_func_share_first:.0f}% to {top_func_share_last:.0f}% across the whole period — the alternative view tells the same story as the stacked bars.",
             "fig_function_time_lines.png")
ax.set_ylabel("Share of tagged studies (%)")
ax.set_xlim(min(years2), max(years2) + 7.1)
ax.set_ylim(0, max(max(max(v) for v in share_by_func.values()), max(label_y.values())) * 1.15)

tick_years = list(range(int(min(years2)), int(max(years2)) + 1, 2))
if years2[-1] not in tick_years:
    tick_years.append(years2[-1])
ax.set_xticks(tick_years)
ax.set_xticklabels(["2026\n(partially)" if y == 2026 else str(y) for y in tick_years])

clean_axes(ax)
ax.grid(axis="both", color="#ddd8cf", linewidth=0.8, zorder=0)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
set_footnote(fig, f"Base: {sum(totals_by_year.values()):,} function tags among the top 5 functions, by publication year. Alternative rendering of fig_function_time.png for design comparison.")
fig.subplots_adjust(left=0.09, right=0.78, top=0.74, bottom=0.18)
fig.savefig(FIGS / "fig_function_time_lines.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 3b. Financing-function output, raw annual counts (stacked area, ALL
# functions, not just the top 5) — mirrors HEE's fig_method_stream.webp,
# swapping economic-evaluation type for financing function.
# ---------------------------------------------------------------------------
ms_funcs = [fn for fn in FUNC_GRPS if fn != "Unclear"]
ms_by_year = defaultdict(Counter)
for s, g in zip(function_j["s"], function_j["g"]):
    fn = FUNC_GRPS[g]
    if fn in ms_funcs:
        ms_by_year[year_of_study[s]][fn] += 1
ms_years = sorted(y for y in ms_by_year if y != 2026)
ms_totals = [sum(ms_by_year[y].values()) for y in ms_years]
ms_order = sorted(ms_funcs, key=lambda fn: -sum(ms_by_year[y].get(fn, 0) for y in ms_years))
ms_palette = {fn: FUNCTION_COLORS.get(fn, "#8FA6B8") for fn in ms_order}

fig, ax = plt.subplots(figsize=(9, 5.6))
bottom_ms = np.zeros(len(ms_years))
stacks_ms = {fn: np.array([ms_by_year[y].get(fn, 0) for y in ms_years]) for fn in ms_order}
for fn in ms_order:
    vals = stacks_ms[fn]
    ax.fill_between(ms_years, bottom_ms, bottom_ms + vals, color=ms_palette[fn],
                     label=SHORT_FN.get(fn, fn), zorder=3, alpha=0.92)
    bottom_ms = bottom_ms + vals
growth_ms = round(ms_totals[-1] / ms_totals[0], 1)
top_share_first = round(100 * stacks_ms[ms_order[0]][0] / ms_totals[0])
top_share_last = round(100 * stacks_ms[ms_order[0]][-1] / ms_totals[-1])
set_headline(ax, "Financing-function output is growing across the board",
             "Annual count of financing-function tags, by function (a study can carry more than one, so "
             "totals exceed the study count).",
             f"Total tags grew {growth_ms}× from {ms_years[0]} to {ms_years[-1]}; "
             f"{ms_order[0]}'s share moved from {top_share_first}% to {top_share_last}% of that total.",
             "fig_method_stream.png")
ax.set_ylabel("financing-function tags per year")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
ax.set_xlim(ms_years[0], ms_years[-1])
clean_axes(ax)
ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False, fontsize=8)
set_footnote(fig, f"Base: {sum(ms_totals):,} financing-function tags, {ms_years[0]}–{ms_years[-1]} "
                   f"({ms_years[-1] + 1} partial year omitted).")
fig.tight_layout()
fig.savefig(FIGS / "fig_method_stream.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Outcome domain counts
#    Custom treatment for this figure only: light-to-dark blue by count,
#    larger value labels, a more compact x-axis, and wrapped long category labels.
# ---------------------------------------------------------------------------
outcome_counts = Counter()
for g in outcome_j["g"]:
    outcome_counts[OUTCOME_GRPS[g]] += 1
top_outcome, top_outcome_n = outcome_counts.most_common(1)[0]
_, (second_outcome, second_outcome_n) = outcome_counts.most_common(2)

out_items = sorted(outcome_counts.items(), key=lambda kv: kv[1])
out_labels = [k for k, _ in out_items]
out_values = [v for _, v in out_items]
out_wrapped = ["\n".join(textwrap.wrap(label, width=34, break_long_words=False)) for label in out_labels]

# Use a balanced blue↔orange palette like the design reference: lower-count domains
# shade through cool blues, middle values pass through a very light neutral tint,
# and higher-count domains shade through warm oranges. We map by ordered position
# rather than raw value so the gradient reads clearly even with a very dominant top category.
out_cmap = mcolors.LinearSegmentedColormap.from_list(
    "outcome_blue_orange",
    ["#0b4fb3", "#73a5ea", "#d8e5f4", "#f4c4a4", "#ff8b3d", "#ff5a00"]
)
out_colors = [out_cmap(t) for t in np.linspace(0, 1, len(out_values))]

# Give this chart extra width and explicit subplot margins so long wrapped labels
# do not squeeze the plotting area into a narrow strip.
fig, ax = plt.subplots(figsize=(10.6, max(4.9, 0.55 * len(out_labels) + 1.2)))
ax.barh(out_wrapped, out_values, color=out_colors, zorder=3)

xmax = max(out_values) * 1.24
ax.set_xlim(0, xmax)
label_pad = max(out_values) * 0.022
for y, v in enumerate(out_values):
    ax.text(v + label_pad, y, f"{v:,}", va="center", fontsize=11.5,
            fontweight="bold", color=INK)

set_headline(ax, "One outcome domain dominates the rest",
             "Studies by outcome domain — a study can carry more than one.",
             f"{top_outcome} is tagged {round(top_outcome_n / second_outcome_n, 1)}× as often as "
             f"{second_outcome} ({top_outcome_n:,} vs {second_outcome_n:,}), the next largest domain.",
             "fig_outcome_bar.png")
ax.set_xlabel("studies", fontsize=11)
ax.tick_params(axis="x", labelsize=10)
ax.tick_params(axis="y", labelsize=10.5)
clean_axes(ax)
ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=5))
set_footnote(fig, f"Base: {sum(outcome_counts.values()):,} outcome-domain tags across {N:,} studies.")
fig.subplots_adjust(left=0.34, right=0.92, top=0.78, bottom=0.18)
fig.savefig(FIGS / "fig_outcome_bar.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# Alternative option: lollipop chart for the same outcome-domain distribution.
fig, ax = plt.subplots(figsize=(10.8, max(4.9, 0.56 * len(out_labels) + 1.25)))
ypos = np.arange(len(out_wrapped))
ax.hlines(ypos, 0, out_values, color=out_colors, linewidth=2.2, zorder=1)
ax.scatter(out_values, ypos, s=150, c=out_colors, edgecolors="white", linewidths=1.2, zorder=3)
ax.set_yticks(ypos)
ax.set_yticklabels(out_wrapped)
ax.set_ylim(-0.8, len(out_wrapped) - 0.2)
ax.set_xlim(0, xmax)
for y, v in zip(ypos, out_values):
    ax.text(v + label_pad, y, f"{v:,}", va="center", ha="left", fontsize=11,
            fontweight="bold", color=INK)
set_headline(ax, "One outcome domain dominates the rest",
             "Alternative view: lollipop chart of studies by outcome domain — a study can carry more than one.",
             f"{top_outcome} is tagged {round(top_outcome_n / second_outcome_n, 1)}× as often as "
             f"{second_outcome} ({top_outcome_n:,} vs {second_outcome_n:,}), the next largest domain.",
             "fig_outcome_lollipop.png")
ax.set_xlabel("studies", fontsize=11)
ax.tick_params(axis="x", labelsize=10)
ax.tick_params(axis="y", labelsize=10.5)
clean_axes(ax)
ax.grid(axis="x", color="#edf2f6", linewidth=0.8, zorder=0)
ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=5))
set_footnote(fig, f"Base: {sum(outcome_counts.values()):,} outcome-domain tags across {N:,} studies.")
fig.subplots_adjust(left=0.34, right=0.92, top=0.78, bottom=0.18)
fig.savefig(FIGS / "fig_outcome_lollipop.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 5-8. Study design / type of analysis / data type / data source
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
# 9. Geographic scope
# ---------------------------------------------------------------------------
pct_single = dict_json["meta"]["pct_single"]
hbar(col_counts("geo_scope"), "Most research names a single country",
     "Geographic scope of the analysis population.",
     f"{pct_single}% of studies name a single country; the rest are multi-country or region/global in scope.",
     "fig_scope_bar.png", f"Base: {N:,} studies (analysis population).")

# ---------------------------------------------------------------------------
# 10. Studies by income group
# ---------------------------------------------------------------------------
income_counts = Counter()
for s, c in zip(geo_j["s"], geo_j["c"]):
    inc = countries[c]["income"]
    if inc:
        income_counts[inc] += 1
inc_order = dict_json["meta"]["inc_lv"]
income_counts_ordered = {k: income_counts.get(k, 0) for k in inc_order}
inc_ranked = sorted(income_counts_ordered.items(), key=lambda kv: -kv[1])
top_income, top_income_n = inc_ranked[0]
second_income, second_income_n = inc_ranked[1]
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(list(income_counts_ordered.keys()), list(income_counts_ordered.values()),
       color=[dict_json["meta"]["pal_inc"][i] for i in range(len(inc_order))], zorder=3, width=0.62)
ax.margins(x=0.06)
set_headline(ax, f"{top_income} settings carry the largest share of study-country pairs",
             "Study-country pairs by income group.",
             f"{top_income} accounts for {top_income_n:,} study-country pairs, ahead of "
             f"{second_income}'s {second_income_n:,}.", "fig_income_bar.png")
ax.set_ylabel("studies")
clean_axes(ax)
ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
set_footnote(fig, f"Base: {sum(income_counts_ordered.values()):,} study-country pairs with a known income group.")
fig.tight_layout()
fig.savefig(FIGS / "fig_income_bar.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 11. Top 20 countries
# ---------------------------------------------------------------------------
country_counts = Counter()
for c in geo_j["c"]:
    country_counts[countries[c]["country"]] += 1
n_countries = len(country_counts)
top_country, top_country_n = country_counts.most_common(1)[0]
_, (second_country, second_country_n) = country_counts.most_common(2)
hbar(country_counts, "One country dominates the evidence base",
     "Top 20 countries by study count — a multi-country study is counted once per country it names.",
     f"{top_country} leads with {top_country_n:,} study-country pairs, "
     f"{round(top_country_n / second_country_n, 1)}× {second_country}'s {second_country_n:,}.",
     "fig_top_countries.png",
     f"Base: {sum(country_counts.values()):,} study-country pairs across {n_countries} countries.",
     top=20, gradient=True)

# ---------------------------------------------------------------------------
# 11b. Bivariate map: disease burden x research volume, by country. Mirrors
# HEE's fig_map_bivariate.webp (same 3x3 tertile design, same "where high
# burden meets low evidence" framing) — the only figure needing real country
# geometry, rendered via Plotly+kaleido (bundled here as a map-tile renderer
# only) and composited into the usual matplotlib headline/footnote layout.
# ---------------------------------------------------------------------------
if HAVE_PLOTLY:
    BIVAR_PALETTE = [
        "#ede6d6", "#a8d0e6", "#3d8ec9",   # burden low:  evidence low, mid, high
        "#dba394", "#a99bab", "#5b83ab",   # burden mid:  evidence low, mid, high
        "#c1442e", "#9c5769", "#4b3f72",   # burden high: evidence low, mid, high
    ]
    dfb = pd.DataFrame(countries)
    dfb_valid = dfb[dfb["dalys"].notna()].copy()
    dfb_valid["burden_t"] = pd.qcut(dfb_valid["dalys"].rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
    dfb_valid["evid_t"] = pd.qcut(dfb_valid["studies"].rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
    dfb_valid["code"] = dfb_valid["burden_t"] * 3 + dfb_valid["evid_t"]
    n_no_burden = len(dfb) - len(dfb_valid)

    tmp_png = FIGS / "_tmp_bivariate_map.png"
    render_discrete_map_png(dfb_valid["iso3"].tolist(), dfb_valid["code"].tolist(), BIVAR_PALETTE, tmp_png)

    worst = dfb_valid[(dfb_valid["burden_t"] == 2) & (dfb_valid["evid_t"] == 0)].sort_values("dalys", ascending=False)
    n_worst = len(worst)

    bv_headline = f"{n_worst} countries carry the highest disease burden but the least research"
    bv_desc = ("Each country by its total disease burden (GBD 2023 DALYs) and its count of HFF studies naming "
               "it, in tertiles. Deep red = high burden, little research; blue = well-researched relative to "
               "burden; dark purple = high on both; cream = low on both.")
    bv_finding = (f"{', '.join(worst['country'].tolist()[:5])} fall in the highest-burden, lowest-evidence "
                  f"cell — top third globally for disease burden, bottom third for HFF research volume.")
    FIG_META["fig_map_bivariate.png"] = (bv_headline, bv_desc, bv_finding)

    fig = plt.figure(figsize=(11, 8))
    ax_map = fig.add_axes([0.03, 0.10, 0.94, 0.62])
    ax_map.imshow(plt.imread(tmp_png))
    ax_map.axis("off")
    ax_map.set_facecolor(PAPER)

    leg = fig.add_axes([0.06, 0.015, 0.13, 0.13])
    for by in range(3):
        for bx in range(3):
            leg.add_patch(plt.Rectangle((bx, by), 1, 1, facecolor=BIVAR_PALETTE[by * 3 + bx],
                                         edgecolor=PAPER, linewidth=1.5))
    leg.set_xlim(-0.5, 3.3)
    leg.set_ylim(-0.5, 3.3)
    leg.annotate("", xy=(3.15, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=INK, linewidth=1))
    leg.annotate("", xy=(0, 3.15), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=INK, linewidth=1))
    leg.text(1.5, -0.4, "Evidence →", ha="center", va="top", fontsize=8.5, color=INK)
    leg.text(-0.4, 1.5, "Burden →", ha="right", va="center", fontsize=8.5, color=INK, rotation=90)
    leg.set_xticks([]); leg.set_yticks([])
    for spine in leg.spines.values():
        spine.set_visible(False)

    fig.text(0.02, 0.975, D(bv_headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.930, D(bv_desc), fontsize=9.5, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.880, D(bv_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    fig.text(0.99, 0.02, f"Burden: GBD 2023 all-cause DALYs (IHME), whole-country. Evidence: HFF studies naming "
                          f"the country. Robinson projection. {n_no_burden} countr" +
             ("y lacks" if n_no_burden == 1 else "ies lack") + " burden data (rendered grey).",
             fontsize=7.6, color=SUBHEAD_COLOR, ha="right", va="bottom")
    fig.patch.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_map_bivariate.png", dpi=150)
    plt.close(fig)
    tmp_png.unlink(missing_ok=True)

# ---------------------------------------------------------------------------
# 11c. Country burden & equity set. Disease burden (GBD 2023 DALYs) crossed
# with HFF research volume, mirroring HEE's own burden/equity/inequality
# figures. All reuse the same base country table.
# ---------------------------------------------------------------------------
INC_ORDER = dict_json["meta"]["inc_lv"]
INC_COLORS = dict(zip(INC_ORDER, dict_json["meta"]["pal_inc"]))

cdf = pd.DataFrame(countries)
cdf_b = cdf[cdf["dalys"].notna()].copy()
cdf_b["per100k"] = cdf_b["studies"] / (cdf_b["dalys"] / 1e5)
TOTAL_DALY_ALL = cdf_b["dalys"].sum()
TOTAL_STUDIES_ALL = cdf_b["studies"].sum()
cdf_b["expected"] = TOTAL_STUDIES_ALL * cdf_b["dalys"] / TOTAL_DALY_ALL
cdf_b["deficit"] = cdf_b["studies"] - cdf_b["expected"]
burden_pts = cdf_b[(cdf_b["studies"] > 0) & (cdf_b["pop"].notna())].copy()


def income_legend(ax_or_fig, loc="lower right", ncol=1, **kw):
    handles = [plt.Rectangle((0, 0), 1, 1, color=INC_COLORS[i]) for i in INC_ORDER]
    return ax_or_fig.legend(handles, INC_ORDER, loc=loc, ncol=ncol, frameon=False, fontsize=8.5, **kw)


def income_legend_below(ax):
    return income_legend(ax, loc="upper center", ncol=4, bbox_to_anchor=(0.5, -0.13))


# --- fig_burden: research intensity (studies per 100k DALYs) vs total burden ---
med_by_inc = burden_pts.groupby("income")["per100k"].median()
hi_med, lo_med = med_by_inc.get("High income"), med_by_inc.get("Low income")
hilo_ratio = round(hi_med / lo_med) if (hi_med and lo_med) else None

fig, ax = plt.subplots(figsize=(9.5, 6.5))
for inc in INC_ORDER:
    sub = burden_pts[burden_pts["income"] == inc]
    ax.scatter(sub["dalys"], sub["per100k"].clip(lower=0.005), s=(sub["pop"] / 3e5).clip(lower=15),
               color=INC_COLORS[inc], alpha=0.75, edgecolors="white", linewidths=0.4, zorder=3, label=inc)
label_rows = pd.concat([
    burden_pts.nlargest(2, "per100k"),
    burden_pts[burden_pts["per100k"] > 0].nsmallest(3, "per100k"),
    burden_pts.nlargest(2, "dalys"),
]).drop_duplicates(subset="country")
for _, r in label_rows.iterrows():
    ax.annotate(r["country"], xy=(r["dalys"], max(r["per100k"], 0.005)), xytext=(5, 4),
                textcoords="offset points", fontsize=8, color=INK)
ax.set_xscale("log")
ax.set_yscale("log")
set_headline(ax, "The poorest countries carry the most disease and the least research",
             "Each point is a country: research intensity (studies per unit of disease burden) against total burden.",
             f"The median high-income country has {hilo_ratio}× more HFF studies per 100,000 DALYs than "
             f"the median low-income country.",
             "fig_burden.png")
ax.set_xlabel("Total disease burden (DALYs, 2023, log scale)")
ax.set_ylabel("HFF studies per 100,000 DALYs (log scale)")
clean_axes(ax)
income_legend_below(ax)
set_footnote(fig, f"Base: {len(burden_pts):,} countries with GBD 2023 burden data and ≥1 study. Point area "
                   f"∝ population.")
fig.tight_layout()
fig.savefig(FIGS / "fig_burden.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# --- fig_deficit: studies vs. a burden-proportional expected share ---
rows_d = pd.concat([cdf_b.nsmallest(12, "deficit"), cdf_b.nlargest(10, "deficit")]).copy()
rows_d["plot_val"] = -rows_d["deficit"]
rows_d = rows_d.sort_values("plot_val")
plot_labels_d = [SHORT_COUNTRY.get(c, c) for c in rows_d["country"]]
colors_d = [INC_COLORS.get(i, GREY) for i in rows_d["income"]]
fig, ax = plt.subplots(figsize=(10.8, 8.6))
ax.barh(plot_labels_d, rows_d["plot_val"], color=colors_d, zorder=3)

max_abs_d = float(np.nanmax(np.abs(rows_d["plot_val"])))
xpad_d = max_abs_d * 0.12
ax.set_xlim(-(max_abs_d + xpad_d), max_abs_d + xpad_d)
ax.axvline(0, color="#8a8272", linewidth=1.1, zorder=2)

for y, v in enumerate(rows_d["plot_val"]):
    label = f"{abs(int(round(v))):,}"
    if v >= 0:
        ax.text(v + max_abs_d * 0.02, y, label, va="center", ha="left", fontsize=8.8, color=INK)
    else:
        ax.text(v - max_abs_d * 0.02, y, label, va="center", ha="right", fontsize=8.8, color=INK)

biggest_deficit = cdf_b.loc[cdf_b["deficit"].idxmin()]
biggest_surplus = cdf_b.loc[cdf_b["deficit"].idxmax()]
set_headline(ax, "Studies vs. a burden-proportional expected share",
             "If research were proportional to disease burden, each country would hold a share of studies equal "
             "to its share of global DALYs. Bars right = below that expected count; left = above.",
             f"{biggest_deficit['country']} has about {abs(round(biggest_deficit['deficit'])):,} fewer studies "
             f"than a burden-proportional share; the largest surplus sits in {biggest_surplus['country']} "
             f"(+{round(biggest_surplus['deficit']):,}).",
             "fig_deficit.png")
ax.set_xlabel("studies below (+) / above (−) a burden-proportional share")
ax.tick_params(axis="y", labelsize=10)
ax.tick_params(axis="x", labelsize=9.5)
clean_axes(ax)
ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
ax.text(0.02, 1.0, "Above expected", transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color=SUBHEAD_COLOR)
ax.text(0.98, 1.0, "Below expected", transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=SUBHEAD_COLOR)
income_legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"{x:+,.0f}" if x != 0 else "0"))
ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=6, symmetric=True))
set_footnote(fig, f"Expected = {int(TOTAL_STUDIES_ALL):,} study-country pairs × (country DALYs ÷ total "
                   f"DALYs). GBD 2023 all-cause DALYs (IHME).")
fig.subplots_adjust(left=0.23, right=0.95, top=0.77, bottom=0.17)
fig.savefig(FIGS / "fig_deficit.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# --- fig_equity_time: share of single-country research about LMICs, over time ---
lv_scope = LV["geo_scope"]
single_code = lv_scope.index("Single country")
s_to_cs = defaultdict(set)
for s, c in zip(geo_j["s"], geo_j["c"]):
    s_to_cs[s].add(c)
income_of_c = {i: r["income"] for i, r in enumerate(countries)}
by_year_tot_eq, by_year_lmic_eq = Counter(), Counter()
for s, cs in s_to_cs.items():
    if studies["geo_scope"][s] != single_code or len(cs) != 1:
        continue
    inc = income_of_c.get(next(iter(cs)))
    if inc is None:
        continue
    y = studies["year"][s]
    by_year_tot_eq[y] += 1
    if inc != "High income":
        by_year_lmic_eq[y] += 1
yrs_eq = sorted(y for y in by_year_tot_eq if y != 2026)
share_eq = [100 * by_year_lmic_eq.get(y, 0) / by_year_tot_eq[y] for y in yrs_eq]
lmic_burden_share = 100 * cdf_b[cdf_b["income"] != "High income"]["dalys"].sum() / cdf_b["dalys"].sum()

fig, ax = plt.subplots(figsize=(8.5, 5.2))
ax.fill_between(yrs_eq, share_eq, color="#c0392b", alpha=0.12, zorder=1)
ax.plot(yrs_eq, share_eq, color="#c0392b", linewidth=2.75, marker="o", markersize=4, zorder=3)
ax.axhline(lmic_burden_share, color=SUBHEAD_COLOR, linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
ax.text(yrs_eq[0], lmic_burden_share + 2, f"LMIC share of global disease burden — {lmic_burden_share:.0f}%",
        fontsize=9, color=SUBHEAD_COLOR)
set_headline(ax, "Research about LMICs is rising, but still far below their burden share",
             "Share of each year's single-country studies that are about low- and middle-income countries.",
             f"It climbed from {share_eq[0]:.0f}% in {yrs_eq[0]} to {share_eq[-1]:.0f}% in {yrs_eq[-1]} — real "
             f"progress, yet still far below the {lmic_burden_share:.0f}% of global disease burden LMICs carry.",
             "fig_equity_time.png")
ax.set_ylabel("share of single-country studies about LMICs (%)")
ax.set_ylim(0, 100)
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
clean_axes(ax)
ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
set_footnote(fig, f"Base: single-country studies with a known income group, by publication year; "
                   f"{yrs_eq[-1] + 1} (partial) omitted. Burden reference: LMIC share of GBD 2023 all-cause DALYs.")
fig.tight_layout()
fig.savefig(FIGS / "fig_equity_time.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# --- fig_inequality: Lorenz curve of LMIC evidence vs. LMIC burden ---
lmic_df = cdf_b[cdf_b["income"] != "High income"].sort_values("per100k").copy()
lmic_df["cum_daly"] = lmic_df["dalys"].cumsum() / lmic_df["dalys"].sum()
lmic_df["cum_studies"] = lmic_df["studies"].cumsum() / lmic_df["studies"].sum()
x_l = np.concatenate([[0], lmic_df["cum_daly"].values])
y_l = np.concatenate([[0], lmic_df["cum_studies"].values])
gini = 1 - 2 * np.trapezoid(y_l, x_l)
mid_mask = lmic_df["cum_daly"] <= 0.5
half_share = 100 * lmic_df.loc[mid_mask, "cum_studies"].max() if mid_mask.any() else 0
top5_share = 100 * lmic_df.nlargest(5, "studies")["studies"].sum() / lmic_df["studies"].sum()

fig, ax = plt.subplots(figsize=(8, 7.8))
ax.plot([0, 1], [0, 1], color="#8a8272", linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
ax.fill_between(x_l, x_l, y_l, color="#c0392b", alpha=0.12, zorder=1)
ax.plot(x_l, y_l, color="#c0392b", linewidth=2.5, zorder=3)
ax.scatter([0.5], [half_share / 100], color=INK, zorder=4, s=45)
ax.annotate(f"Countries carrying the least-served half of\nLMIC disease burden hold only {half_share:.0f}% of "
            f"the LMIC evidence", xy=(0.5, half_share / 100), xytext=(0.52, half_share / 100 + 0.12),
            fontsize=9.5, fontweight="bold", color=INK)
set_headline(ax, "Evidence is concentrated in a few LMICs",
             "Low- and middle-income countries ordered from least to most research per unit of disease burden.",
             f"The five most-studied LMICs hold {top5_share:.0f}% of the LMIC evidence (Gini = {gini:.2f}).",
             "fig_inequality.png")
ax.set_xlabel("cumulative share of LMIC disease burden (DALYs)")
ax.set_ylabel("cumulative share of LMIC evidence")
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
clean_axes(ax)
set_footnote(fig, f"Base: {len(lmic_df)} LMIC countries with GBD 2023 burden data. Eligible HFF studies naming "
                   f"each country vs. GBD 2023 DALYs.")
fig.tight_layout()
fig.savefig(FIGS / "fig_inequality.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# --- fig_injustice: country research-to-burden ratio by income group ---
inj_pts = burden_pts.copy()
INJ_TOTAL_STUDY_COUNTRY_PAIRS = inj_pts["studies"].sum()
INJ_TOTAL_DALYS = inj_pts["dalys"].sum()
inj_pts["research_to_burden"] = (
    (inj_pts["studies"] / INJ_TOTAL_STUDY_COUNTRY_PAIRS) /
    (inj_pts["dalys"] / INJ_TOTAL_DALYS)
)
inj_pts["log2_research_to_burden"] = np.log2(inj_pts["research_to_burden"])

fig, ax = plt.subplots(figsize=(9.5, 6.8))
income_x = {inc: i for i, inc in enumerate(INC_ORDER)}
rng = np.random.default_rng(20261007)
inj_pts["plot_x"] = [income_x[inc] + rng.uniform(-0.16, 0.16) for inc in inj_pts["income"]]
for inc in INC_ORDER:
    sub = inj_pts[inj_pts["income"] == inc]
    ax.scatter(sub["plot_x"], sub["log2_research_to_burden"], s=38,
               color=INC_COLORS[inc], alpha=0.72, edgecolors="white", linewidths=0.45, zorder=3)
    median = sub["log2_research_to_burden"].median()
    ax.scatter(income_x[inc], median, marker="_", s=520, linewidths=3, color=INK, zorder=5)

ax.axhline(0, color="#8a8272", linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
ax.text(3.42, 0.12, "Proportional to burden", ha="right", va="bottom",
        fontsize=8.5, color=SUBHEAD_COLOR)

label_rows = pd.concat([
    inj_pts[inj_pts["income"] == "Low income"].nsmallest(1, "log2_research_to_burden"),
    inj_pts[inj_pts["income"] == "Lower middle income"].nsmallest(1, "log2_research_to_burden"),
    inj_pts.nlargest(1, "log2_research_to_burden"),
]).drop_duplicates(subset="country")
for _, r in label_rows.iterrows():
    offset_y = -11 if r["log2_research_to_burden"] < 0 else 6
    ax.annotate(r["country"], xy=(r["plot_x"], r["log2_research_to_burden"]), xytext=(5, offset_y),
                textcoords="offset points", fontsize=8, fontweight="bold", color=INK)

n_below = int((inj_pts["research_to_burden"] < 1).sum())
below = inj_pts[inj_pts["research_to_burden"] < 1]
pct_low_below = round(100 * below["income"].isin(["Low income", "Lower middle income"]).mean())
set_headline(ax, "Research is less abundant relative to disease burden in poorer countries",
             "Each point is a country. Values below zero indicate a smaller share of HFF studies than the "
             "country's share of global disease burden.",
             f"{n_below} of {len(inj_pts)} countries have a smaller research share than burden share; "
             f"{pct_low_below}% of these are low- or lower-middle-income.",
             "fig_injustice.png")
ax.set_xticks(range(len(INC_ORDER)), INC_ORDER)
ax.set_xlim(-0.45, len(INC_ORDER) - 0.55)
ax.set_xlabel("World Bank income group")
ax.set_ylabel("Research relative to disease burden (log2 ratio)")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
clean_axes(ax)
ax.grid(False)
ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
ax.text(0.01, 0.98, "More research than burden share", transform=ax.transAxes,
        ha="left", va="top", fontsize=8.5, color=SUBHEAD_COLOR)
ax.text(0.01, 0.02, "Less research than burden share", transform=ax.transAxes,
        ha="left", va="bottom", fontsize=8.5, color=SUBHEAD_COLOR)
set_footnote(fig, f"Base: {len(inj_pts):,} countries with GBD 2023 burden data and ≥1 study; shares use this same "
                   f"country universe. GBD 2023 all-cause DALYs (IHME).\nCountry research counts are study-country "
                   f"pairs: a multi-country study counts once per country. Equatorial Guinea and Djibouti have "
                   f"burden data but no identified studies and are not plotted. Horizontal markers show medians.")
fig.tight_layout()
fig.savefig(FIGS / "fig_injustice.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# --- fig_funder_scorecard: burden/intensity scatter + ranked deficit bar, side
# by side. Mirrors HEE's own fig_funder_scorecard: a shaded "high burden, low
# evidence" priority zone and a global-rate reference line on the scatter,
# labelled deficit countries, a top-anchored income legend, and a 15-country
# (not 12) deficit bar to match that reference exactly. ---
TOP_N_DEFICIT_SC = 15
top_deficit_sc = cdf_b.nsmallest(TOP_N_DEFICIT_SC, "deficit").sort_values("deficit", ascending=False)
fig = plt.figure(figsize=(13.5, 7.4))
ax1 = fig.add_axes([0.055, 0.12, 0.44, 0.58])
for inc in INC_ORDER:
    sub = burden_pts[burden_pts["income"] == inc]
    ax1.scatter(sub["dalys"], sub["per100k"].clip(lower=0.005), s=(sub["pop"] / 3.5e5).clip(lower=12),
                color=INC_COLORS[inc], alpha=0.75, edgecolors="white", linewidths=0.4, zorder=3)
ax1.set_xscale("log")
ax1.set_yscale("log")

# Priority zone: the higher-burden half of countries, below the rate a
# perfectly burden-proportional allocation would give every country alike.
global_rate_100k = TOTAL_STUDIES_ALL / TOTAL_DALY_ALL * 1e5
x_min_sc, x_max_sc = burden_pts["dalys"].min() * 0.8, burden_pts["dalys"].max() * 1.3
y_min_sc, y_max_sc = burden_pts["per100k"].clip(lower=0.005).min() * 0.7, burden_pts["per100k"].max() * 1.4
ax1.set_xlim(x_min_sc, x_max_sc)
ax1.set_ylim(y_min_sc, y_max_sc)
zone_x0 = burden_pts["dalys"].median()
ax1.axhline(global_rate_100k, color="#8a8272", linewidth=1, linestyle=(0, (4, 3)), zorder=2)
ax1.add_patch(plt.Rectangle((zone_x0, y_min_sc), x_max_sc - zone_x0, global_rate_100k - y_min_sc,
                             facecolor="#c0392b", alpha=0.08, edgecolor="none", zorder=1))
zone_text_sc = "priority zone\nhigh burden, low evidence"
zone_tx_sc, zone_ty_sc = zone_x0 * 2.2, y_min_sc * 2.6
ax1.text(zone_tx_sc, zone_ty_sc, zone_text_sc,
         ha="left", va="center", fontsize=8.5, fontweight="bold", color="#a13a2a", linespacing=1.4)

label_rows_sc = burden_pts[burden_pts["country"].isin(top_deficit_sc["country"])].sort_values("dalys")
declutter_labels(ax1, label_rows_sc, "dalys", "per100k", name_map=SHORT_COUNTRY,
                  avoid=[(zone_tx_sc, zone_ty_sc, "left", zone_text_sc)])

ax1.set_xlabel("Disease burden (DALYs, 2023, log)")
ax1.set_ylabel("Studies per 100,000 DALYs (log)")
clean_axes(ax1)

ax2 = fig.add_axes([0.58, 0.12, 0.4, 0.58])
ax2.barh([SHORT_COUNTRY.get(c, c) for c in top_deficit_sc["country"]], -top_deficit_sc["deficit"],
         color=[INC_COLORS.get(i, GREY) for i in top_deficit_sc["income"]], zorder=3)
for y, v in enumerate(-top_deficit_sc["deficit"]):
    ax2.text(v, y, f" +{v:,.0f}", va="center", fontsize=8.5, color=INK)
ax2.set_xlabel("studies short of a burden-proportional share")
ax2.set_title(f"The {TOP_N_DEFICIT_SC} largest evidence deficits", fontsize=11, fontweight="bold",
              color=INK, loc="left")
clean_axes(ax2)

sc_headline = "Funding priority scorecard"
sc_desc = (f"Where economic evidence is most absent relative to disease burden (left, shaded), and the "
           f"{TOP_N_DEFICIT_SC} countries with the largest absolute shortfall (right).")
sc_finding = (f"{biggest_deficit['country']} alone is {abs(round(biggest_deficit['deficit'])):,} studies short "
              f"of a burden-proportional share — the largest gap of any country.")
FIG_META["fig_funder_scorecard.png"] = (sc_headline, sc_desc, sc_finding)
fig.text(0.02, 0.965, D(sc_headline.upper()), fontsize=17, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.915, D(sc_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
fig.text(0.02, 0.882, D(sc_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
income_legend(fig, loc="upper left", ncol=4, bbox_to_anchor=(0.02, 0.80))
fig.text(0.01, 0.03, f"Base: {len(burden_pts):,} countries with GBD 2023 burden data and ≥1 study. Point "
                     f"area ∝ population. Expected = study-country pairs × (country DALYs ÷ total DALYs).",
         fontsize=8, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
fig.patch.set_facecolor(PAPER)
ax1.set_facecolor(PAPER)
ax2.set_facecolor(PAPER)
fig.savefig(FIGS / "fig_funder_scorecard.png", dpi=150)
plt.close(fig)

# --- fig_reach_time: cumulative country coverage by income group, over time ---
first_year_of_c = {}
for s, c in zip(geo_j["s"], geo_j["c"]):
    y = studies["year"][s]
    if c not in first_year_of_c or y < first_year_of_c[c]:
        first_year_of_c[c] = y
years_rt = list(range(dict_json["years"][0], 2026))
reach_series = {}
for inc in INC_ORDER:
    idxs = cdf.index[cdf["income"] == inc].tolist()
    n_total = len(idxs)
    reach_series[inc] = [100 * sum(1 for i in idxs if first_year_of_c.get(i, 9999) <= y) / n_total
                          for y in years_rt]
first_full = {inc: next((y for y, v in zip(years_rt, reach_series[inc]) if v >= 100), None) for inc in INC_ORDER}
fastest = min((k for k in first_full if first_full[k]), key=lambda k: first_full[k])
last_to_95 = max(next((y for y, v in zip(years_rt, reach_series[inc]) if v >= 95), years_rt[-1]) for inc in INC_ORDER)

fig, ax = plt.subplots(figsize=(8.5, 5.4))
for inc in INC_ORDER:
    ax.plot(years_rt, reach_series[inc], color=INC_COLORS[inc], linewidth=2.5, marker="o", markersize=3.5,
             label=inc, zorder=3)
set_headline(ax, "Coverage came fast, and roughly together, across income groups",
             "Cumulative share of each World Bank income group's countries with ≥1 HFF study naming it, by year.",
             f"{fastest} countries reached full coverage first, by {first_full[fastest]}; every income group "
             f"passed 95% coverage by {last_to_95}.",
             "fig_reach_time.png")
ax.set_ylabel("share of income group's countries with ≥1 study (%)")
ax.set_ylim(0, 105)
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
clean_axes(ax)
ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
ax.legend(loc="lower right", frameon=False, fontsize=8.5)
set_footnote(fig, f"Base: countries reached by ≥1 eligible HFF study naming them, by first year named; "
                   f"{years_rt[-1] + 1} (partial) excluded.")
fig.tight_layout()
fig.savefig(FIGS / "fig_reach_time.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# --- fig_top_producers: rank by total studies vs. rank per 10M people, top 15 ---
prod = cdf_b[cdf_b["studies"] > 0].copy()
prod["per10m"] = prod["studies"] / (prod["pop"] / 1e7)
prod["rank_total"] = prod["studies"].rank(ascending=False, method="min")
prod["rank_percap"] = prod["per10m"].rank(ascending=False, method="min")
top15p = prod.nsmallest(15, "rank_total").sort_values("rank_total")


def _rank_color(r):
    if r["rank_percap"] < r["rank_total"] - 2:
        return ACCENT
    if r["rank_percap"] > r["rank_total"] + 2:
        return "#c0392b"
    return GREY



# Positions are each country's ORDER within this top-15 set (always evenly
# spaced 1..15), not the literal rank value — the real rank_total/rank_percap
# numbers (which can differ by 100+) are printed in the labels instead. Same
# convention as fig_function_bump_eras.png's bump chart: a log axis on the
# literal values crowds ranks 10-15 into unreadable overlap, since log(11/10)
# is tiny next to log(2/1).
top15p = top15p.copy()
top15p["pos_total"] = range(1, len(top15p) + 1)
top15p["pos_percap"] = top15p["rank_percap"].rank(method="first").astype(int)

fig, ax = plt.subplots(figsize=(9, 8.5))
for _, r in top15p.iterrows():
    col = _rank_color(r)
    name = SHORT_COUNTRY.get(r["country"], r["country"])
    ax.plot([0, 1], [r["pos_total"], r["pos_percap"]], color=col, marker="o", markersize=6.5,
             linewidth=2, zorder=3)
    ax.text(-0.05, r["pos_total"], f"{name} ({int(r['rank_total'])})", ha="right", va="center",
            fontsize=9, color=INK)
    ax.text(1.05, r["pos_percap"], f"{name} ({int(r['rank_percap'])})", ha="left", va="center",
            fontsize=9, color=INK)
ax.set_xlim(-0.85, 1.85)
ax.set_ylim(len(top15p) + 0.6, 0.4)
ax.set_xticks([0, 1], ["By total\nstudies", "Per 10M\npeople"], fontsize=10)
ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(False)
top15p_delta = (top15p["rank_total"] - top15p["rank_percap"])
biggest_faller = top15p.loc[top15p_delta.idxmin()]
biggest_riser = top15p.loc[top15p_delta.idxmax()]
set_headline(ax, "The biggest producers of HFF evidence are not the best-served",
             "The 15 countries with the most HFF studies, ranked by total volume and again per 10 million "
             "people. A line falling to the right is a country whose standing rests on its size.",
             f"{biggest_faller['country']} falls from rank {int(biggest_faller['rank_total'])} to "
             f"{int(biggest_faller['rank_percap'])} per capita; {biggest_riser['country']} climbs from "
             f"{int(biggest_riser['rank_total'])} to {int(biggest_riser['rank_percap'])}.",
             "fig_top_producers.png")
set_footnote(fig, f"Base: {len(prod)} countries with ≥1 study. Population: World Bank.")
fig.tight_layout()
fig.savefig(FIGS / "fig_top_producers.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# --- fig_function_outcome_heatmap: outcome-domain mix of each financing function ---
# s_to_funcs_fo / s_to_outs_fo (study -> tag set, each excluding "Unclear") are reused
# below by fig_authorship_outcome_heatmap.png and fig_funder_outcome_heatmap.png.
s_to_funcs_fo = defaultdict(set)
for s, g in zip(function_j["s"], function_j["g"]):
    fn = FUNC_GRPS[g]
    if fn != "Unclear":
        s_to_funcs_fo[s].add(fn)
s_to_outs_fo = defaultdict(set)
for s, g in zip(outcome_j["s"], outcome_j["g"]):
    o = OUTCOME_GRPS[g]
    if o != "Unclear":
        s_to_outs_fo[s].add(o)

fo_outs = [o for o in OUTCOME_GRPS if o != "Unclear"]
fo_counts = {fn: Counter() for fn in ms_funcs}
fo_totals = Counter()
for s, funcs in s_to_funcs_fo.items():
    outs = s_to_outs_fo.get(s)
    if not outs:
        continue
    for fn in funcs:
        fo_totals[fn] += 1
        for o in outs:
            fo_counts[fn][o] += 1

fo_grid = np.array([[100 * fo_counts[fn][o] / fo_totals[fn] if fo_totals[fn] else 0 for o in fo_outs]
                     for fn in ms_funcs])
# Cleaner table-style heatmap: light-to-dark teal, wrapped column headers,
# row labels split over two lines, white cell borders, and a horizontal legend.
fo_cmap = mcolors.LinearSegmentedColormap.from_list(
    "fo", ["#deedf0", "#c7e3e6", "#97d1d5", "#4ea8b0", "#0b5964"]
)

fo_xlabels = {
    "Economic development": "Economic\ndevelopment",
    "Efficiency in the use of resources": "Efficiency\nin resource\nuse",
    "Equitable distribution of health system resources": "Equitable\ndistribution",
    "Financial protection": "Financial\nprotection",
    "Improved level and distribution of health": "Improved\nhealth\nlevel/dist.",
    "Other": "Other",
    "Quality of service provision": "Quality of\nservice\nprovision",
    "Responsiveness to citizens": "Responsiveness\nto citizens",
    "Transparency and accountability": "Transparency\nand\naccountability",
}
fo_rowlabels = {
    "Benefits decisions": "Benefits decisions",
    "Capital investment: infrastructure": "Capital investment:\ninfrastructure",
    "Capital investment: other health system inputs": "Capital investment:\nother health system inputs",
    "Other": "Other",
    "Pooling": "Pooling",
    "Public financial management": "Public financial\nmanagement",
    "Purchasing": "Purchasing",
    "Recurrent financing for the procurement and distribution of supply chain inputs": "Recurrent financing\n(supply chain)",
    "Revenue Raising": "Revenue Raising",
    "Revenue raising": "Revenue Raising",
}

fig, ax = plt.subplots(figsize=(14.2, 9.6))
fo_vmax = max(60, float(np.nanmax(fo_grid)))
im = ax.imshow(fo_grid, cmap=fo_cmap, aspect="auto", vmin=0, vmax=fo_vmax)

ax.set_xticks(range(len(fo_outs)))
ax.set_xticklabels([fo_xlabels.get(o, SHORT_OUT.get(o, o)) for o in fo_outs],
                   fontsize=10.4, fontweight="bold", ha="center", linespacing=1.06)
ax.xaxis.tick_top()
ax.tick_params(axis="x", top=False, bottom=False, pad=10)

# Manual row labels let the bold function name and lighter n-count occupy
# separate vertical zones, preventing overlap even for two-line labels.
ax.set_yticks(range(len(ms_funcs)))
ax.set_yticklabels([""] * len(ms_funcs))
ax.tick_params(axis="y", left=False, pad=8)
for i, fn in enumerate(ms_funcs):
    row_label = fo_rowlabels.get(fn, SHORT_FN.get(fn, fn))
    n_lines = row_label.count("\n") + 1
    name_y = i - (0.17 if n_lines >= 2 else 0.10)
    count_y = i + (0.31 if n_lines >= 2 else 0.24)
    ax.text(-1.07, name_y, row_label, ha="right", va="center",
            fontsize=10.8, fontweight="bold", color=INK, linespacing=0.98, clip_on=False)
    ax.text(-1.07, count_y, f"(n={fo_totals[fn]:,})", ha="right", va="center",
            fontsize=9.8, color=SUBHEAD_COLOR, clip_on=False)

# Crisp white dividers create the clean table appearance in the reference.
ax.set_xticks(np.arange(-0.5, len(fo_outs), 1), minor=True)
ax.set_yticks(np.arange(-0.5, len(ms_funcs), 1), minor=True)
ax.grid(which="minor", color="white", linestyle="-", linewidth=1.15)
ax.tick_params(which="minor", bottom=False, left=False, top=False)

for i in range(len(ms_funcs)):
    for j in range(len(fo_outs)):
        v = fo_grid[i, j]
        ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=10.5,
                fontweight="bold", color="white" if v >= 32 else INK)
for spine in ax.spines.values():
    spine.set_visible(False)

fo_top_i, fo_top_j = np.unravel_index(np.argmax(fo_grid), fo_grid.shape)
fo_top_fn, fo_top_o = ms_funcs[fo_top_i], fo_outs[fo_top_j]
fo_top_val = fo_grid[fo_top_i, fo_top_j]
set_headline(ax, "Each financing function reports a different outcome mix",
             "Outcome-domain mix of each financing function's tagged studies (row shares; a study can "
             "carry more than one tag of either kind, so rows needn't sum to 100%).",
             f"{fo_top_val:.0f}% of {SHORT_FN.get(fo_top_fn, fo_top_fn)} studies report "
             f"{SHORT_OUT.get(fo_top_o, fo_top_o)}, its most common outcome.",
             "fig_function_outcome_heatmap.png")

# Keep editorial text comfortably clear of the top column headers.
headline_texts = ax.texts[-3:]
headline_texts[0].set_position((0, 1.50))
headline_texts[1].set_position((0, 1.355))
headline_texts[2].set_position((0, 1.21))

# Match the reference: short horizontal scale under the table with descriptor
# sitting to the right instead of under the scale.
fig.subplots_adjust(left=0.27, right=0.985, top=0.72, bottom=0.16)
cbar_ax = fig.add_axes([0.34, 0.075, 0.35, 0.025])
cbar = fig.colorbar(im, cax=cbar_ax, orientation="horizontal")
cbar_ticks = list(range(0, int(fo_vmax) + 1, 10))
cbar.set_ticks(cbar_ticks)
cbar.set_ticklabels([f"{x}%" for x in cbar_ticks])
cbar.ax.tick_params(labelsize=8.8, colors=SUBHEAD_COLOR, length=3, pad=2)
cbar.outline.set_visible(False)
fig.text(0.71, 0.087, "Share of tagged studies (%)", ha="left", va="center",
         fontsize=10.2, color=INK)

set_footnote(fig, f"Base: {N:,} studies; cross-tab of financing_function × outcome_domain tags, both "
                   f"excluding 'Unclear'.")
fig.savefig(FIGS / "fig_function_outcome_heatmap.png", dpi=150, bbox_inches="tight")
plt.close(fig)

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

# ---------------------------------------------------------------------------
# 11d-pre. Forest plot: adjusted odds ratios by income group. HEE's version
# modelled "reports a comparable metric" and "has a local author" — is_quant
# (type_of_analysis == Quantitative) stands in for the former; the v2
# extraction's author_affiliation_countries now gives a REAL "has a local
# author" variable for the latter (previously substituted with has_doi).
# Adjusted for era, on single-country studies with a known income group. No
# statsmodels dependency — irls_logit() is a from-scratch IRLS implementation
# (defined near the top of this file).
# ---------------------------------------------------------------------------
single_code_fp = LV["geo_scope"].index("Single country")
s_to_c_fp = defaultdict(set)
for s, c in zip(geo_j["s"], geo_j["c"]):
    s_to_c_fp[s].add(c)
lv_toa_fp = LV["type_of_analysis"]
era_lv_fp = LV["era"]
fp_rows = []
for s in range(N):
    if studies["geo_scope"][s] != single_code_fp:
        continue
    cs = s_to_c_fp.get(s)
    if not cs or len(cs) != 1:
        continue
    ci = next(iter(cs))
    inc = income_of_c.get(ci)
    if inc is None:
        continue
    ac = author_countries_of_s.get(s)
    local_author = float(iso3_of_c.get(ci) in ac) if ac else np.nan
    fp_rows.append({
        "income": inc,
        "era2018": 1.0 if era_lv_fp[studies["era"][s]] == "2018-2026" else 0.0,
        "has_local_author": local_author,
        "is_quant": 1.0 if lv_toa_fp[studies["type_of_analysis"][s]] == "Quantitative" else 0.0,
    })
fp_df = pd.DataFrame(fp_rows)
fp_inc_levels = [i for i in INC_ORDER if i != "High income"]


def fp_design(outcome_col):
    d = fp_df.dropna(subset=[outcome_col]).copy()
    for inc in fp_inc_levels:
        d[f"inc_{inc}"] = (d["income"] == inc).astype(float)
    d["intercept"] = 1.0
    cols = ["intercept"] + [f"inc_{inc}" for inc in fp_inc_levels] + ["era2018"]
    return d[cols].values.astype(float), d[outcome_col].values.astype(float), cols


fp_panels = [("has_local_author", "Has a local author"), ("is_quant", "Uses a quantitative analysis")]
fp_results = {}
for outcome, panel_title in fp_panels:
    Xfp, yfp, cols_fp = fp_design(outcome)
    beta_fp, cov_fp = irls_logit(Xfp, yfp)
    se_fp = np.sqrt(np.diag(cov_fp))
    rows_fp = []
    for inc in fp_inc_levels:
        i = cols_fp.index(f"inc_{inc}")
        orv = np.exp(beta_fp[i])
        lo = np.exp(beta_fp[i] - 1.96 * se_fp[i])
        hi = np.exp(beta_fp[i] + 1.96 * se_fp[i])
        rows_fp.append((inc, orv, lo, hi))
    fp_results[panel_title] = rows_fp

fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
inc_colors_fp = dict(zip(dict_json["meta"]["inc_lv"], dict_json["meta"]["pal_inc"]))
for ax, (panel_title, rows_fp) in zip(axes, fp_results.items()):
    ys = list(range(len(rows_fp)))
    for y, (inc, orv, lo, hi) in zip(ys, rows_fp):
        col = inc_colors_fp.get(inc, GREY)
        ax.plot([lo, hi], [y, y], color=col, linewidth=2, zorder=3)
        ax.scatter([orv], [y], color=col, s=70, zorder=4)
        ax.text(hi, y, f"  {orv:.2f}", va="center", fontsize=9, color=INK)
    ax.axvline(1, color="#8a8272", linewidth=1, linestyle=(0, (4, 3)), zorder=2)
    ax.set_yticks(ys, [inc for inc, *_ in rows_fp], fontsize=9.5)
    ax.set_xscale("log")
    ax.set_xlabel("adjusted odds ratio vs. high income (log)")
    ax.set_title(panel_title, fontsize=11, fontweight="bold", color=INK, loc="left")
    ax.set_ylim(-0.6, len(rows_fp) - 0.4)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#c9c3b3")
    ax.spines["bottom"].set_color("#c9c3b3")
    ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)

local_rows = fp_results["Has a local author"]
quant_rows = fp_results["Uses a quantitative analysis"]
lowest_quant = min(quant_rows, key=lambda r: r[1])
lowest_local = min(local_rows, key=lambda r: r[1])
n_local_model = int(fp_df["has_local_author"].notna().sum())
fp_headline = "Lower-income studies are far less likely to use a quantitative analysis or a local author"
fp_desc = ("Adjusted odds ratios from two logistic models on single-country studies with a known income "
           "group. Reference group is high-income studies (OR=1). Adjusted for era; observational, so "
           "associations not causes.")
fp_finding = (f"{lowest_quant[0]} studies have {lowest_quant[1]:.2f}× the odds of a high-income study of "
              f"using a quantitative analysis, and {lowest_local[1]:.2f}× the odds of {lowest_local[0]} "
              f"studies having a local author.")
FIG_META["fig_forest.png"] = (fp_headline, fp_desc, fp_finding)
fig.suptitle("")
fig.text(0.02, 0.99, D(fp_headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.02, 0.95, D(fp_desc), fontsize=9, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
fig.text(0.02, 0.865, D(fp_finding), fontsize=9.5, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
fig.text(0.01, -0.02, f"Base: {len(fp_df):,} single-country studies with a known income group (is_quant "
                      f"model); {n_local_model:,} of those also have a recovered author affiliation country "
                      f"(has_local_author model). From type_of_analysis and author_affiliation_countries.",
         fontsize=7.6, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
fig.patch.set_facecolor(PAPER)
for ax in axes:
    ax.set_facecolor(PAPER)
fig.tight_layout(rect=[0, 0.02, 1, 0.80])
fig.savefig(FIGS / "fig_forest.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# 11d-authors. Local-authorship-by-country table, shared by fig_funder_capacity
# below and fig_map_authorship further down (inside the HAVE_PLOTLY block).
# ---------------------------------------------------------------------------
local_by_country = defaultdict(lambda: [0, 0])  # ci -> [n_local, n_with_known_affiliation]
for s in range(N):
    if studies["geo_scope"][s] != single_code_fp:
        continue
    cs = s_to_c_fp.get(s)
    if not cs or len(cs) != 1:
        continue
    ci = next(iter(cs))
    ac = author_countries_of_s.get(s)
    if ac is None:
        continue
    rec = local_by_country[ci]
    rec[1] += 1
    if iso3_of_c.get(ci) in ac:
        rec[0] += 1

if have_authors:
    # --- fig_collab_chord: cross-income co-authorship chord diagram ---
    CHORD_ORDER = ["High income", "Upper middle income", "Lower middle income", "Low income"]
    chord_pair_counts = Counter()
    chord_whole_counts = Counter()
    for s, ac in author_countries_of_s.items():
        incs = {income_by_iso3[iso3] for iso3 in ac if iso3 in income_by_iso3}
        if not incs:
            continue
        if len(incs) == 1:
            chord_whole_counts[next(iter(incs))] += 1
            continue
        incs_ordered = sorted(incs, key=CHORD_ORDER.index)
        for i in range(len(incs_ordered)):
            for j in range(i + 1, len(incs_ordered)):
                chord_pair_counts[(incs_ordered[i], incs_ordered[j])] += 1

    chord_degree = {n: 0 for n in CHORD_ORDER}
    for (a, b), v in chord_pair_counts.items():
        chord_degree[a] += v
        chord_degree[b] += v
    chord_total_degree = sum(chord_degree.values()) or 1

    chord_gap = np.radians(3.0)
    chord_spans = {n: (chord_degree[n] / chord_total_degree) * (2 * np.pi - chord_gap * len(CHORD_ORDER))
                   for n in CHORD_ORDER}
    chord_start = {}
    _a = np.pi / 2
    for n in CHORD_ORDER:
        chord_start[n] = _a
        _a -= (chord_spans[n] + chord_gap)

    chord_node_pairs = {n: [] for n in CHORD_ORDER}
    for (a, b), v in chord_pair_counts.items():
        chord_node_pairs[a].append((b, v))
        chord_node_pairs[b].append((a, v))
    for n in CHORD_ORDER:
        chord_node_pairs[n].sort(key=lambda pv: CHORD_ORDER.index(pv[0]))

    chord_seg = {}  # (node, partner) -> (theta_start, theta_end), both consumed clockwise (decreasing)
    for n in CHORD_ORDER:
        cursor = chord_start[n]
        deg_n = chord_degree[n] or 1
        for partner, v in chord_node_pairs[n]:
            width = (v / deg_n) * chord_spans[n]
            chord_seg[(n, partner)] = (cursor, cursor - width)
            cursor -= width


    def _arc_pts(a1, a2, r, npts=24):
        return [(r * np.cos(t), r * np.sin(t)) for t in np.linspace(a1, a2, npts)]


    chord_palette = dict(zip(CHORD_ORDER, [inc_colors_fp[n] for n in CHORD_ORDER]))
    fig, ax = plt.subplots(figsize=(9, 9))
    R = 1.0
    for (a, b), v in chord_pair_counts.items():
        seg_a, seg_b = chord_seg[(a, b)], chord_seg[(b, a)]
        poly = _arc_pts(*seg_a, R) + [(0.0, 0.0)] + _arc_pts(*seg_b, R) + [(0.0, 0.0)]
        xs, ys = zip(*poly)
        ax.fill(xs, ys, color=chord_palette[a], alpha=0.55, zorder=2, linewidth=0)
    for n in CHORD_ORDER:
        a1, a2 = chord_start[n], chord_start[n] - chord_spans[n]
        xs, ys = zip(*_arc_pts(a1, a2, R * 1.05, 60))
        ax.plot(xs, ys, color=chord_palette[n], linewidth=16, solid_capstyle="butt", zorder=3)
        mid = (a1 + a2) / 2
        lx, ly = R * 1.16 * np.cos(mid), R * 1.16 * np.sin(mid)
        deg = np.degrees(mid % (2 * np.pi))
        ax.text(lx, ly, n, ha="center", va="center", fontsize=10.5, fontweight="bold", color=INK,
                rotation=(90 - deg if deg < 180 else 270 - deg))
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect("equal")
    ax.axis("off")

    n_cross = sum(chord_pair_counts.values())
    n_whole_hi = chord_whole_counts.get("High income", 0)
    n_whole_lo = chord_whole_counts.get("Low income", 0)
    chord_headline = "High-income teams are the hub of cross-income collaboration"
    chord_desc = (f"Cross-income co-authorship of {n_cross + sum(chord_whole_counts.values()):,} studies with a "
                  f"known author-affiliation country. Ribbons: studies co-authored across two income groups "
                  f"(within-group studies excluded from the ribbons).")
    chord_finding = (f"Most evidence isn't cross-income at all: {n_whole_hi:,} studies are wholly "
                      f"high-income-authored; just {n_whole_lo:,} wholly low-income.")
    FIG_META["fig_collab_chord.png"] = (chord_headline, chord_desc, chord_finding)
    fig.text(0.02, 0.99, D(chord_headline), fontsize=15, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.955, D(chord_desc), fontsize=9, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.895, D(chord_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top",
             style="italic", wrap=True)
    fig.text(0.5, 0.015, "Affiliations from author_affiliation_countries; World Bank income groups.",
             fontsize=7.6, color=SUBHEAD_COLOR, ha="center", va="bottom")
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_collab_chord.png", dpi=150)
    plt.close(fig)

else:
    print("Skipping fig_collab_chord.png: no recognised author-affiliation countries.")

if have_authors:
    # --- fig_funder_capacity: local authorship share vs. disease burden ---
    fc_rows = []
    for c, (n_local, n_tot) in local_by_country.items():
        if n_tot < 5:
            continue
        r = countries[c]
        if r.get("dalys") is None:
            continue
        fc_rows.append({"country": r["country"], "income": r["income"], "dalys": r["dalys"],
                         "share": 100 * n_local / n_tot, "n": n_tot})
    fc_df = pd.DataFrame(fc_rows)

    fig, ax = plt.subplots(figsize=(9.5, 7))
    for inc in INC_ORDER:
        sub = fc_df[fc_df["income"] == inc]
        ax.scatter(sub["share"], sub["dalys"], s=(sub["n"] / 3).clip(lower=15), color=INC_COLORS[inc],
                   alpha=0.75, edgecolors="white", linewidths=0.4, zorder=3, label=inc)
    low_share_high_burden = fc_df[(fc_df["share"] < 50) & (fc_df["dalys"] > fc_df["dalys"].median())].nlargest(6, "dalys")
    for _, r in low_share_high_burden.iterrows():
        ax.annotate(SHORT_COUNTRY.get(r["country"], r["country"]), xy=(r["share"], r["dalys"]), xytext=(5, 4),
                    textcoords="offset points", fontsize=8, fontweight="bold", color=INK)
    ax.set_yscale("log")
    fcap_headline = "Where to build local research capacity"
    fcap_desc = "Each country by disease burden and the share of its studies with a local author."
    if len(low_share_high_burden):
        w = low_share_high_burden.iloc[0]
        fcap_finding = f"{w['country']}: high burden, only {w['share']:.0f}% local authorship."
    else:
        fcap_finding = "No country combines very high burden with very low local authorship."
    set_headline(ax, fcap_headline, fcap_desc, fcap_finding, "fig_funder_capacity.png")
    ax.set_xlabel("share of the country's studies with a local author (%)")
    ax.set_ylabel("disease burden (DALYs, 2023, log)")
    clean_axes(ax)
    income_legend_below(ax)
    set_footnote(fig, f"Base: {len(fc_df)} countries with ≥5 single-country studies with a known "
                       f"author-affiliation country. Local authorship is a proxy for research capacity, not "
                       f"its full measure.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_funder_capacity.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

else:
    print("Skipping fig_funder_capacity.png: no recognised author-affiliation countries.")

# --- fig_authorship_pattern: local / mixed / foreign authorship, by income group ---
if have_authors:
    pattern_counts = {inc: Counter() for inc in INC_ORDER}
    for s in range(N):
        if studies["geo_scope"][s] != single_code_fp:
            continue
        cs = s_to_c_fp.get(s)
        if not cs or len(cs) != 1:
            continue
        ci = next(iter(cs))
        inc = income_of_c.get(ci)
        ac = author_countries_of_s.get(s)
        if inc is None or ac is None:
            continue
        local_iso3 = iso3_of_c.get(ci)
        if ac == {local_iso3}:
            cat = "Local authors only"
        elif local_iso3 in ac:
            cat = "Local and foreign"
        else:
            cat = "Foreign authors only"
        pattern_counts[inc][cat] += 1

    pat_cats = ["Local authors only", "Local and foreign", "Foreign authors only"]
    pat_colors = {"Local authors only": ACCENT, "Local and foreign": GREY, "Foreign authors only": "#e0752f"}
    pat_incomes = [i for i in INC_ORDER if sum(pattern_counts[i].values()) > 0]
    pat_shares = {inc: [100 * pattern_counts[inc][cat] / sum(pattern_counts[inc].values()) for cat in pat_cats]
                  for inc in pat_incomes}

    fig, ax = plt.subplots(figsize=(10, max(2.6, 0.75 * len(pat_incomes) + 1)))
    ys = list(range(len(pat_incomes)))[::-1]  # High income at top, Low income at bottom
    for y, inc in zip(ys, pat_incomes):
        left = 0.0
        for cat in pat_cats:
            v = pat_shares[inc][pat_cats.index(cat)]
            ax.barh(y, v, left=left, color=pat_colors[cat], zorder=3)
            if v >= 6:
                txt_color = INK if cat == "Local and foreign" else "white"
                ax.text(left + v / 2, y, f"{v:.0f}%", ha="center", va="center", fontsize=9.5,
                        color=txt_color, fontweight="bold")
            left += v
    ax.set_yticks(ys, pat_incomes, fontsize=9.5)
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_xlabel("share of single-country studies")
    legend_handles_pat = [plt.Rectangle((0, 0), 1, 1, color=pat_colors[c]) for c in pat_cats]
    ax.legend(legend_handles_pat, pat_cats, loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=3, frameon=False, fontsize=9.5)

    lowest_local_inc = min(pat_incomes, key=lambda i: pat_shares[i][pat_cats.index("Local authors only")])
    lowest_local_share = pat_shares[lowest_local_inc][pat_cats.index("Local authors only")]
    foreign_only_low = pat_shares[lowest_local_inc][pat_cats.index("Foreign authors only")]
    pat_headline = "Research about the poorest countries is rarely led locally"
    pat_desc = "Author-affiliation pattern of single-country studies, by the income group studied."
    pat_finding = (f"Only {lowest_local_share:.0f}% of {lowest_local_inc} studies have a local-only author "
                   f"team, and {foreign_only_low:.0f}% have no local author at all.")
    set_headline(ax, pat_headline, pat_desc, pat_finding, "fig_authorship_pattern.png")
    clean_axes(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(left=False)
    ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
    set_footnote(fig, f"Base: {sum(sum(pattern_counts[i].values()) for i in pat_incomes):,} single-country "
                       f"studies with a known income group and a recovered author-affiliation country. From "
                       f"author_affiliation_countries.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_authorship_pattern.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

# --- fig_authorship_by_function: local-authorship rate, by financing function ---
if have_authors:
    s_to_funcs_af = defaultdict(set)
    for s, g in zip(function_j["s"], function_j["g"]):
        fn = FUNC_GRPS[g]
        if fn != "Unclear":
            s_to_funcs_af[s].add(fn)

    func_local_counts = {fn: [0, 0] for fn in ms_funcs}
    for s in range(N):
        if studies["geo_scope"][s] != single_code_fp:
            continue
        cs = s_to_c_fp.get(s)
        if not cs or len(cs) != 1:
            continue
        ci = next(iter(cs))
        if income_of_c.get(ci) is None:
            continue
        ac = author_countries_of_s.get(s)
        if ac is None:
            continue
        local = iso3_of_c.get(ci) in ac
        funcs = s_to_funcs_af.get(s)
        if not funcs:
            continue
        for fn in funcs:
            rec = func_local_counts[fn]
            rec[1] += 1
            if local:
                rec[0] += 1

    afn_items = sorted(
        ((fn, 100 * nl / nk, nk) for fn, (nl, nk) in func_local_counts.items() if nk >= 20),
        key=lambda t: t[1])
    afn_labels = [SHORT_FN.get(fn, fn) for fn, _, _ in afn_items]
    afn_values = [v for _, v, _ in afn_items]

    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.5 * len(afn_items) + 1)))
    ax.barh(afn_labels, afn_values, color=ACCENT, zorder=3)
    for y, v in enumerate(afn_values):
        ax.text(v, y, f"  {v:.0f}%", va="center", fontsize=9, color=INK)
    most_foreign_fn, most_foreign_v = afn_items[0][0], afn_items[0][1]
    most_local_fn, most_local_v = afn_items[-1][0], afn_items[-1][1]
    afl_headline = f"{SHORT_FN.get(most_foreign_fn, most_foreign_fn)} research is the most foreign-led"
    afl_desc = "Share of single-country studies with a local author, by financing function tag."
    afl_finding = (f"Only {most_foreign_v:.0f}% of {SHORT_FN.get(most_foreign_fn, most_foreign_fn)} studies "
                   f"have a local author, vs. {most_local_v:.0f}% for "
                   f"{SHORT_FN.get(most_local_fn, most_local_fn)}.")
    set_headline(ax, afl_headline, afl_desc, afl_finding, "fig_authorship_by_function.png")
    ax.set_xlabel("share of single-country studies with a local author (%)")
    ax.set_xlim(0, 100)
    clean_axes(ax)
    set_footnote(fig, f"Base: single-country studies with a known income group, a recovered author-"
                       f"affiliation country, and >=1 financing-function tag; functions with <20 such "
                       f"studies excluded. A study can carry >1 function tag.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_authorship_by_function.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

# --- fig_authorship_outcome_heatmap: authorship pattern, by outcome domain ---
if have_authors:
    outcome_auth_counts = {o: Counter() for o in fo_outs}
    for s in range(N):
        if studies["geo_scope"][s] != single_code_fp:
            continue
        cs = s_to_c_fp.get(s)
        if not cs or len(cs) != 1:
            continue
        ci = next(iter(cs))
        if income_of_c.get(ci) is None:
            continue
        ac = author_countries_of_s.get(s)
        if ac is None:
            continue
        local_iso3 = iso3_of_c.get(ci)
        if ac == {local_iso3}:
            cat = "Local authors only"
        elif local_iso3 in ac:
            cat = "Local and foreign"
        else:
            cat = "Foreign authors only"
        outs = s_to_outs_fo.get(s)
        if not outs:
            continue
        for o in outs:
            outcome_auth_counts[o][cat] += 1

    ao_cats = ["Local authors only", "Local and foreign", "Foreign authors only"]
    ao_order = sorted(fo_outs, key=lambda o: -sum(outcome_auth_counts[o].values()))
    ao_row_totals = {o: sum(outcome_auth_counts[o].values()) for o in ao_order}
    ao_grid = np.array([[100 * outcome_auth_counts[o][cat] / ao_row_totals[o] if ao_row_totals[o] else 0
                          for cat in ao_cats] for o in ao_order])
    ao_cmap = mcolors.LinearSegmentedColormap.from_list("ao", ["#eef5f5", "#4f8f96", "#123a40"])

    fig, ax = plt.subplots(figsize=(11, max(3, 0.55 * len(ao_order) + 1)))
    im = ax.imshow(ao_grid, cmap=ao_cmap, aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(ao_cats)))
    ax.set_xticklabels(ao_cats, fontsize=9, rotation=15, ha="right")
    ax.set_yticks(range(len(ao_order)))
    ax.set_yticklabels([f"{SHORT_OUT.get(o, o)}  (n={ao_row_totals[o]:,})" for o in ao_order], fontsize=9)
    for i, o in enumerate(ao_order):
        for j, cat in enumerate(ao_cats):
            v = ao_grid[i, j]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=9, color="white" if v > 55 else INK)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(bottom=False, left=False)
    ao_top_i = int(np.argmin(ao_grid[:, 0]))
    ao_top_o = ao_order[ao_top_i]
    ao_top_val = ao_grid[ao_top_i, 0]
    set_headline(ax, "Some outcome domains are researched more locally than others",
                 "Authorship pattern of single-country studies reporting each outcome domain (row shares).",
                 f"Only {ao_top_val:.0f}% of {SHORT_OUT.get(ao_top_o, ao_top_o)} studies have a local-only "
                 f"author team, the lowest share of any outcome domain.",
                 "fig_authorship_outcome_heatmap.png")
    clean_axes(ax)
    ax.grid(False)
    set_footnote(fig, f"Base: single-country studies with a known income group, a recovered author-"
                       f"affiliation country, and ≥1 outcome-domain tag. A study can carry >1 tag.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_authorship_outcome_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

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

    # Main/original ranked bar version
    ff_desc = "The most-named research funders across studies that report one, after merging name variants into a single entry."
    ff_finding = f"{top_funder_name} is named by {top_funder_n:,} studies, more than any other funder."
    hbar(
        {k: v for k, v in top_funders},
        "A handful of funders dominate the funded evidence",
        ff_desc,
        ff_finding,
        "fig_funder_funders.png",
        f"Base: {n_funded:,} of {N:,} studies ({100 * n_funded / N:.1f}%) report a research funder "
        f"(most do not); a study naming >1 funder counts once per funder. From research_funder, "
        f"name-normalized.",
        color=GOLD, top=15, xlabel="studies", gradient=True
    )

    # Additional treemap option — editorial card style with tight gutters,
    # rounded tiles, contrast-aware typography, and automatic font fitting.
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
        "Infectious Diseases": "#2f79b9",
        "Mental Health": "#7965a8",
        "Climate & Health": "#25835f",
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
    priority_desc = (
        "Panel A shows studies classified to each Wellcome priority theme; Panel B shows the top "
        "funders of those studies by theme. Categories are not mutually exclusive."
    )
    priority_finding = (
        f"{leading_theme} has the largest evidence base ({priority_counts[leading_theme]:,} studies); "
        f"{leading_donor} funds the largest number of priority-theme study links."
    )
    FIG_META["fig_wellcome_priorities.png"] = (
        "Funding and evidence across Wellcome priority themes",
        priority_desc,
        priority_finding,
    )

    fig = plt.figure(figsize=(14.2, 8.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[0.82, 1.45], wspace=0.42)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    fig.suptitle("Funding and evidence across Wellcome priority themes", x=0.055, y=0.965,
                 ha="left", fontsize=19, fontweight="bold", color=INK)
    fig.text(0.055, 0.905, priority_desc, ha="left", va="top", fontsize=10.5,
             color=SUBHEAD_COLOR)
    fig.text(0.055, 0.852, priority_finding, ha="left", va="top", fontsize=11,
             fontweight="bold", color=INK)

    bar_values = [priority_counts[theme] for theme in priority_order]
    bar_y = np.arange(len(priority_order))
    ax_a.barh(bar_y, bar_values, color=[priority_colors[t] for t in priority_order],
              height=0.58, zorder=3)
    ax_a.set_yticks(bar_y, priority_order)
    ax_a.invert_yaxis()
    ax_a.set_xlabel("studies")
    ax_a.set_title("Panel A - How much evidence addresses\nWellcome priority themes?",
                   loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=14)
    for y, value in zip(bar_y, bar_values):
        ax_a.text(value, y, f"  {value:,}  ({100 * value / N:.1f}%)",
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

    fig.text(
        0.055, 0.025,
        f"Base: all {N:,} studies. Themes are independent flags and may overlap. Infectious Diseases and "
        "Mental Health use explicit disease/mental-health terms in existing MeSH-derived metadata; Climate "
        "& Health uses explicit climate/heat MeSH terms or the OpenAlex topic 'Climate Change and Health "
        "Impacts'. Panel B disaggregates the top 12 normalized funders overall; a multi-funder study "
        "counts once for each named funder.",
        ha="left", va="bottom", fontsize=8.2, color=SUBHEAD_COLOR, wrap=True,
    )
    fig.subplots_adjust(left=0.055, right=0.97, top=0.73, bottom=0.16)
    fig.savefig(FIGS / "fig_wellcome_priorities.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    treemap_vals = [v for _, v in top_funders]
    scaled_vals = [v / sum(treemap_vals) * (100 * 100) for v in treemap_vals]
    rects = squarify_treemap_balanced(scaled_vals, 0, 0, 100, 100)

    # Muted multi-hue palette, harmonised with the HEE visual family.
    treemap_palette = [
        "#1e6b72", "#58a9b9", "#8ec6cc", "#b6cda8", "#e1c46e",
        "#ca746a", "#ebb06b", "#9fb0c1", "#8ab4df", "#bc9fdd",
        "#bcae9d", "#97bae3", "#a4c79d", "#dcc19a", "#8aaebd",
    ]

    # Use short forms only when a tile is genuinely too small for the full name.
    treemap_short_labels = {
        "Agency for Healthcare Research and Quality": "AHRQ",
        "Canadian Institutes of Health Research": "CIHR",
        "World Health Organization": "WHO",
        "United States Agency for International Development": "USAID",
        "National Institute on Drug Abuse": "NIDA",
        "Robert Wood Johnson Foundation": "RWJF",
        "National Institute for Health Research": "NIHR",
        "Medical Research Council": "MRC",
        "National Health and Medical Research Council": "NHMRC",
        "National Cancer Institute": "NCI",
    }

    def _treemap_luminance(hex_color):
        h = hex_color.lstrip("#")
        r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _treemap_wrap_label(name, area, w):
        # Keep full labels on large/medium tiles. Only abbreviate on small tiles.
        label = name
        if name == "United States Agency for International Development":
            label = "USAID"
        elif area < 260 and name in treemap_short_labels:
            label = treemap_short_labels[name]
        # Dynamic wrap width tracks tile width rather than a fixed character count.
        if w >= 28:
            width = 18
        elif w >= 20:
            width = 15
        elif w >= 14:
            width = 12
        else:
            width = 9
        return "\n".join(textwrap.wrap(label, width=width, break_long_words=False))

    fig, ax = plt.subplots(figsize=(12.4, 7.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.invert_yaxis()
    ax.axis("off")

    # Add all tiles before fitting text so display-coordinate measurements are stable.
    tile_specs = []
    for i, ((name, val), (x, y, w, h)) in enumerate(zip(top_funders, rects)):
        face = treemap_palette[i % len(treemap_palette)]
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.015,rounding_size=0.65",
            facecolor=face, edgecolor=PAPER, linewidth=1.45,
            mutation_aspect=1.0, zorder=2,
        )
        ax.add_patch(patch)
        tile_specs.append((patch, name, val, x, y, w, h, face))

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def _fit_treemap_text(text_value, box_x, box_y, box_w, box_h, patch,
                          color, max_fs, min_fs, va):
        """Shrink text until it fits fully inside the supplied data-coordinate box."""
        p0 = ax.transData.transform((box_x, box_y))
        p1 = ax.transData.transform((box_x + box_w, box_y + box_h))
        max_w_px = abs(p1[0] - p0[0]) * 0.98
        max_h_px = abs(p1[1] - p0[1]) * 0.98
        anchor_y = box_y if va == "top" else box_y + box_h

        fs = float(max_fs)
        while fs >= min_fs:
            txt = ax.text(
                box_x, anchor_y, text_value,
                ha="left", va=va, fontsize=fs, fontweight="bold",
                color=color, linespacing=1.02, clip_on=True, zorder=3,
            )
            txt.set_clip_path(patch)
            fig.canvas.draw()
            bb = txt.get_window_extent(renderer=renderer)
            if bb.width <= max_w_px and bb.height <= max_h_px:
                return txt
            txt.remove()
            fs -= 0.5

        txt = ax.text(
            box_x, anchor_y, text_value,
            ha="left", va=va, fontsize=min_fs, fontweight="bold",
            color=color, linespacing=0.98, clip_on=True, zorder=3,
        )
        txt.set_clip_path(patch)
        return txt

    for patch, name, val, x, y, w, h, face in tile_specs:
        area = w * h
        text_color = "white" if _treemap_luminance(face) < 0.60 else INK
        label = _treemap_wrap_label(name, area, w)

        # Tight internal padding, with entirely separate title and number zones.
        pad_x = max(0.75, min(1.8, w * 0.055))
        pad_y = max(0.70, min(1.6, h * 0.055))
        inner_w = max(w - 2 * pad_x, 0.5)

        # Large tiles can devote more height to the full name; small tiles keep the
        # count zone protected so title and count can never collide.
        if area >= 800:
            title_frac, count_frac = 0.48, 0.25
            title_max, title_min = 18.5, 11.0
            count_max, count_min = 39.0, 25.0
        elif area >= 430:
            title_frac, count_frac = 0.46, 0.25
            title_max, title_min = 14.5, 9.0
            count_max, count_min = 30.0, 20.0
        elif area >= 250:
            title_frac, count_frac = 0.43, 0.24
            title_max, title_min = 11.5, 7.5
            count_max, count_min = 23.0, 16.0
        else:
            title_frac, count_frac = 0.38, 0.22
            title_max, title_min = 9.5, 6.5
            count_max, count_min = 18.0, 12.0

        title_x = x + pad_x
        title_y = y + pad_y
        title_h = max(h * title_frac, 1.0)

        count_x = x + pad_x
        count_h = max(h * count_frac, 1.0)
        count_y = y + h - pad_y - count_h

        _fit_treemap_text(
            label, title_x, title_y, inner_w, title_h, patch,
            text_color, title_max, title_min, "top",
        )
        _fit_treemap_text(
            f"{val:,}", count_x, count_y, inner_w, count_h, patch,
            text_color, count_max, count_min, "bottom",
        )

    set_headline(
        ax,
        "A handful of funders dominate the funded evidence",
        "Alternative view: the same top funders shown as a treemap after merging name variants into single entries.",
        f"{top_funder_name} is named by {top_funder_n:,} studies, more than any other funder.",
        "fig_funder_funders_treemap.png"
    )
    set_footnote(
        fig,
        f"Base: {n_funded:,} of {N:,} studies ({100 * n_funded / N:.1f}%) report a research funder "
        f"(most do not); a study naming >1 funder counts once per funder. From research_funder, "
        f"name-normalized. Area ∝ funded-study count; top 15 funders shown."
    )
    fig.subplots_adjust(left=0.02, right=0.99, top=0.74, bottom=0.08)
    fig.savefig(FIGS / "fig_funder_funders_treemap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_funder_function_heatmap: financing-function mix of each top funder's studies ---
    funder_func_palette = {fn: FUNCTION_COLORS.get(fn, "#8FA6B8") for fn in ms_funcs}
    s_to_funcs_fh = defaultdict(set)
    for s, g in zip(function_j["s"], function_j["g"]):
        fn = FUNC_GRPS[g]
        if fn != "Unclear":
            s_to_funcs_fh[s].add(fn)

    TOP_N_FUNDER_FH = 12  # visual design choice: show the top 12 funders
    top_funder_names_fh = [name for name, _ in sorted(funder_counts.items(), key=lambda kv: -kv[1])[:TOP_N_FUNDER_FH]]
    fh_counts = {f: Counter() for f in top_funder_names_fh}
    fh_study_totals = Counter()
    for s, keys in funders_of_s.items():
        funcs = s_to_funcs_fh.get(s)
        if not funcs:
            continue
        for key in keys:
            f = funder_display_name[key]
            if f not in fh_counts:
                continue
            fh_study_totals[f] += 1
            for fn in funcs:
                fh_counts[f][fn] += 1

    fh_order = sorted(top_funder_names_fh, key=lambda f: -fh_study_totals[f])
    fh_grid = np.array([[100 * fh_counts[f][fn] / fh_study_totals[f] if fh_study_totals[f] else 0
                          for fn in ms_funcs] for f in fh_order])
    fh_cmap = mcolors.LinearSegmentedColormap.from_list("fh", ["#eef5f5", "#4f8f96", "#123a40"])

    # Restore the heatmap as the main output and save the bubble matrix as an
    # additional option. Column headers reuse the fo_rowlabels 1-2 line wraps
    # (same financing-function names, already tuned above) instead of a wider
    # textwrap.fill() that produced 3-4 line headers tall enough to collide
    # with the editorial text; row labels stay single-line, as in
    # fig_funder_outcome_heatmap, since funder names fit fine unwrapped.
    fig, ax = plt.subplots(figsize=(14.2, 12.8))
    im = ax.imshow(fh_grid, aspect="auto", cmap=fh_cmap, vmin=0, vmax=max(60, np.nanmax(fh_grid)))
    ax.set_xticks(np.arange(len(ms_funcs)))
    ax.set_yticks(np.arange(len(fh_order)))
    # fo_rowlabels' wraps (~20-24 char lines) were sized for that figure's
    # wider per-row space; with 9 columns here each line must be much
    # narrower or neighbouring headers collide, hence a tighter wrap here.
    ax.set_xticklabels([textwrap.fill(SHORT_FN.get(fn, fn), width=13, break_long_words=False) for fn in ms_funcs],
                        fontsize=8.6, fontweight="bold", linespacing=1.2)
    ax.set_yticklabels([f"{f}  (n={fh_study_totals[f]:,})" for f in fh_order], fontsize=10, fontweight="bold")
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False, length=0, pad=10)
    for lab in ax.get_xticklabels():
        lab.set_ha("center")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(fh_grid.shape[1] + 1) - .5, minor=True)
    ax.set_yticks(np.arange(fh_grid.shape[0] + 1) - .5, minor=True)
    ax.grid(which="minor", color="white", linestyle='-', linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    maxv = max(60, np.nanmax(fh_grid))
    for i in range(fh_grid.shape[0]):
        for j in range(fh_grid.shape[1]):
            v = fh_grid[i, j]
            txt_color = "white" if v >= maxv * 0.48 else INK
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=9.3,
                    fontweight="bold", color=txt_color)

    fh_top_i, fh_top_j = np.unravel_index(np.argmax(fh_grid), fh_grid.shape)
    fh_top_funder, fh_top_func = fh_order[fh_top_i], ms_funcs[fh_top_j]
    fh_top_val = fh_grid[fh_top_i, fh_top_j]

    set_headline(
        ax,
        "Some top funders lean heavily toward one financing function",
        "Each top funder's financing-function tag mix (share of that funder's tag mentions; a study can carry more than one tag).",
        f"{fh_top_val:.0f}% of {fh_top_funder}'s financing-function tags are {SHORT_FN.get(fh_top_func, fh_top_func)}, its most concentrated pairing among the top {len(fh_order)} funders.",
        "fig_funder_function_heatmap.png"
    )
    # Column headers wrap to 2 lines and sit above the axes (labeltop=True),
    # so push the editorial text further up to keep it clear of them — same
    # fix as fig_function_outcome_heatmap above.
    headline_texts = ax.texts[-3:]
    headline_texts[0].set_position((0, 1.50))
    headline_texts[1].set_position((0, 1.355))
    headline_texts[2].set_position((0, 1.21))

    fig.subplots_adjust(left=0.30, right=0.97, top=0.72, bottom=0.13)
    cbar_ax = fig.add_axes([0.36, 0.055, 0.30, 0.02])
    cbar = fig.colorbar(im, cax=cbar_ax, orientation="horizontal")
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(labelsize=8.5, colors=SUBHEAD_COLOR, length=3, pad=2)
    fig.text(0.685, 0.065, "Share of tagged studies (%)", ha="left", va="center", fontsize=9.5, color=INK)
    set_footnote(fig, f"Base: top {len(fh_order)} funders by study count, restricted to studies with ≥1 financing-function tag. From research_funder (name-normalized) × financing_function.")
    fig.savefig(FIGS / "fig_funder_function_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Additional bubble-matrix option — same column/row-label treatment as the
    # heatmap above (narrow per-column wraps, single-line row labels) so
    # nothing collides with the editorial text or with itself.
    fig, ax = plt.subplots(figsize=(14.2, 12.8))
    fh_xlabels = [textwrap.fill(SHORT_FN.get(fn, fn), width=13, break_long_words=False) for fn in ms_funcs]
    fh_ylabels = [f"{f}  (n={fh_study_totals[f]:,})" for f in fh_order]
    n_rows, n_cols = fh_grid.shape

    ax.set_xlim(-0.5, n_cols - 0.5)
    ax.set_ylim(-0.5, n_rows - 0.5)
    ax.invert_yaxis()
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(fh_xlabels, fontsize=8.6, fontweight="bold", ha="center", linespacing=1.2)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", top=False, bottom=False, pad=10)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(fh_ylabels, fontsize=10, fontweight="bold")
    ax.tick_params(axis="y", left=False, pad=10)

    for x in np.arange(-0.5, n_cols, 1):
        ax.axvline(x, color="#e8edf0", linewidth=1, zorder=0)
    ax.axvline(n_cols - 0.5, color="#e8edf0", linewidth=1, zorder=0)
    for y in np.arange(-0.5, n_rows, 1):
        ax.axhline(y, color="#e8edf0", linewidth=1, zorder=0)
    ax.axhline(n_rows - 0.5, color="#e8edf0", linewidth=1, zorder=0)
    for i in range(n_rows):
        for j in range(n_cols):
            ax.scatter(j, i, s=85, color="#d3d9de", edgecolor="none", zorder=1)

    teal_cmap = mcolors.LinearSegmentedColormap.from_list("bubble_teal", ["#8fd0d8", "#44a8b0", "#0f6b73"])
    for i, f in enumerate(fh_order):
        row_vals = fh_grid[i, :]
        top_idx = np.argsort(row_vals)[-2:]
        for j in range(n_cols):
            v = row_vals[j]
            if v <= 0:
                continue
            if j in top_idx:
                bubble_size = 25 + (v * 17)
                bubble_color = teal_cmap(min(v / 55, 1))
                ax.scatter(j, i, s=bubble_size, color=bubble_color, edgecolor="white", linewidth=1.2, zorder=3)
                ax.text(j + 0.18, i, f"{v:.0f}%", va="center", ha="left", fontsize=9,
                        fontweight="bold", color="#167a8b", zorder=4)

    for spine in ax.spines.values():
        spine.set_visible(False)

    set_headline(
        ax,
        "Funders specialize in different financing functions",
        "Alternative view: bubble matrix of each top funder's financing-function mix. Bubble size and colour intensity both reflect the share of that funder's studies; highlighted bubbles show the largest 1–2 shares in each row.",
        f"{fh_top_val:.0f}% of {fh_top_funder}-funded studies are tagged {SHORT_FN.get(fh_top_func, fh_top_func)}, its top financing function.",
        "fig_funder_function_bubbles.png"
    )
    # Same clearance fix as the heatmap above: column headers sit above the
    # axes, so push the editorial text further up.
    headline_texts = ax.texts[-3:]
    headline_texts[0].set_position((0, 1.50))
    headline_texts[1].set_position((0, 1.355))
    headline_texts[2].set_position((0, 1.21))

    fig.subplots_adjust(left=0.30, right=0.97, top=0.72, bottom=0.17)
    fig.text(0.02, 0.765, "Funder (number of studies)", fontsize=10, fontweight="bold", color=INK, va="bottom")
    fig.text(0.635, 0.765, "Health financing function", fontsize=10, fontweight="bold", color=INK, ha="center", va="bottom")

    legend_ax = fig.add_axes([0.30, 0.015, 0.28, 0.10])
    legend_ax.axis("off")
    legend_ax.text(0.0, 0.85, "Example bubble sizes\n(percentage of studies)", fontsize=9, fontweight="bold", color=INK, va="top")
    legend_sizes = [10, 25, 50]
    legend_xs = [0.55, 0.75, 0.98]
    for x, s in zip(legend_xs, legend_sizes):
        legend_ax.scatter(x, 0.32, s=25 + s * 17, color="#cfd6dd", edgecolor="none")
        legend_ax.text(x, -0.05, f"{s}%", ha="center", va="top", fontsize=8.5, color=INK)
    legend_ax.set_xlim(0, 1.1)
    legend_ax.set_ylim(0, 1)

    note_ax = fig.add_axes([0.62, 0.015, 0.35, 0.10])
    note_ax.axis("off")
    note_ax.text(0.0, 0.85, "Note:", fontsize=9, fontweight="bold", color=INK, va="top")
    note_ax.text(0.0, 0.58, "Highlights the dominant funding focus by funder\n(largest 1–2 percentages in each row).", fontsize=8.8, color=INK, va="top")

    set_footnote(fig, f"Base: top {len(fh_order)} funders by study count, restricted to studies with ≥1 financing-function tag. From research_funder (name-normalized) × financing_function.")
    fig.savefig(FIGS / "fig_funder_function_bubbles.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_funder_outcome_heatmap: outcome-domain mix of each top funder's studies ---
    fu_out_counts = {f: Counter() for f in top_funder_names_fh}
    fu_out_totals = Counter()
    for s, keys in funders_of_s.items():
        outs = s_to_outs_fo.get(s)
        if not outs:
            continue
        for key in keys:
            f = funder_display_name[key]
            if f not in fu_out_counts:
                continue
            fu_out_totals[f] += 1
            for o in outs:
                fu_out_counts[f][o] += 1

    fu_out_order = sorted(top_funder_names_fh, key=lambda f: -fu_out_totals[f])
    fu_out_grid = np.array([[100 * fu_out_counts[f][o] / fu_out_totals[f] if fu_out_totals[f] else 0
                              for o in fo_outs] for f in fu_out_order])
    fu_out_cmap = mcolors.LinearSegmentedColormap.from_list("fuo", ["#eef5f5", "#4f8f96", "#123a40"])

    fig, ax = plt.subplots(figsize=(11, 7.6))
    im = ax.imshow(fu_out_grid, cmap=fu_out_cmap, aspect="auto", vmin=0, vmax=fu_out_grid.max())
    ax.set_xticks(range(len(fo_outs)))
    ax.set_xticklabels([SHORT_OUT.get(o, o) for o in fo_outs], fontsize=8, rotation=28, ha="right")
    ax.set_yticks(range(len(fu_out_order)))
    ax.set_yticklabels([f"{f}  (n={fu_out_totals[f]:,})" for f in fu_out_order], fontsize=9)
    for i, f in enumerate(fu_out_order):
        for j, o in enumerate(fo_outs):
            v = fu_out_grid[i, j]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                    color="white" if v > fu_out_grid.max() * 0.55 else INK)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(bottom=False, left=False)
    fu_out_top_i, fu_out_top_j = np.unravel_index(np.argmax(fu_out_grid), fu_out_grid.shape)
    fu_out_top_f, fu_out_top_o = fu_out_order[fu_out_top_i], fo_outs[fu_out_top_j]
    fu_out_top_val = fu_out_grid[fu_out_top_i, fu_out_top_j]
    set_headline(ax, "Funders back research toward different outcomes",
                 "Outcome-domain mix of each top funder's studies (row shares; a study can carry more than "
                 "one tag, so rows needn't sum to 100%).",
                 f"{fu_out_top_val:.0f}% of {fu_out_top_f}-funded studies report "
                 f"{SHORT_OUT.get(fu_out_top_o, fu_out_top_o)}, its most common outcome.",
                 "fig_funder_outcome_heatmap.png")
    clean_axes(ax)
    ax.grid(False)
    set_footnote(fig, f"Base: top {len(fu_out_order)} funders by study count, restricted to studies with "
                       f"≥1 outcome-domain tag. From research_funder (name-normalized) × "
                       f"outcome_domain.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_funder_outcome_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_funder_function_mix: 100%-stacked financing-function mix, top 8 funders ---
    mix_funders = fh_order[:8]
    fh_tag_totals = {f: sum(fh_counts[f].values()) for f in mix_funders}
    mix_shares = {fn: [100 * fh_counts[f][fn] / fh_tag_totals[f] if fh_tag_totals[f] else 0 for f in mix_funders]
                  for fn in ms_funcs}

    fig, ax = plt.subplots(figsize=(11, max(4.6, 0.55 * len(mix_funders) + 2.6)))
    mix_ys = list(range(len(mix_funders)))[::-1]  # highest-volume funder at top
    left = np.zeros(len(mix_funders))
    for fn in ms_funcs:
        vals = np.array(mix_shares[fn])
        ax.barh(mix_ys, vals, left=left, color=funder_func_palette[fn], label=SHORT_FN.get(fn, fn), zorder=3)
        left += vals
    ax.set_yticks(mix_ys, mix_funders, fontsize=9.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of the funder's financing-function tags (%)")
    mix_best = max(((f, fn, mix_shares[fn][i]) for i, f in enumerate(mix_funders) for fn in ms_funcs),
                   key=lambda t: t[2])
    mix_funder, mix_func, mix_val = mix_best
    mix_headline = "Some top funders lean heavily toward one financing function"
    mix_desc = ("Each top funder's financing-function tag mix (share of that funder's tag mentions; a study "
                "can carry more than one tag).")
    mix_finding = (f"{mix_val:.0f}% of {mix_funder}'s financing-function tags are "
                   f"{SHORT_FN.get(mix_func, mix_func)}, its most concentrated pairing among the top "
                   f"{len(mix_funders)} funders.")
    set_headline(ax, mix_headline, mix_desc, mix_finding, "fig_funder_function_mix.png")
    clean_axes(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(left=False)
    # A 9-entry legend is wider than this chart's bar area at 3 columns —
    # anchoring it to the figure (not the axes) stops that width from forcing
    # the axes to shrink to stay centered under it, but the legend still has
    # to physically fit inside the figure's own width or bbox_inches="tight"
    # pads the saved PNG out around it, which makes the (unchanged) axes look
    # small against the now-larger canvas. 2 columns + explicit margins avoid
    # both failure modes.
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.235),
               bbox_transform=fig.transFigure, ncol=2, frameon=False, fontsize=8.5)
    set_footnote(fig, f"Base: top {len(mix_funders)} funders by study count, restricted to studies with "
                       f"≥1 financing-function tag. From research_funder (name-normalized) × "
                       f"financing_function.")
    fig.subplots_adjust(left=0.28, right=0.97, top=0.72, bottom=0.34)
    fig.savefig(FIGS / "fig_funder_function_mix.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_funder_trend: top funders' share of that year's funded studies, over time ---
    TOP_N_TREND = 6
    trend_funders = [f for f, _ in sorted(funder_counts.items(), key=lambda kv: -kv[1])[:TOP_N_TREND]]
    by_year_funder = defaultdict(Counter)
    year_funded_totals = Counter()
    for s, keys in funders_of_s.items():
        yr = year_of_study[s]
        year_funded_totals[yr] += 1
        for key in keys:
            f = funder_display_name[key]
            if f in trend_funders:
                by_year_funder[f][yr] += 1
    trend_years = sorted(y for y in year_funded_totals if 2013 <= y <= 2025)

    fig, ax = plt.subplots(figsize=(10, 6.4))
    trend_cmap = plt.get_cmap("tab10")
    for i, f in enumerate(trend_funders):
        shares = [100 * by_year_funder[f].get(y, 0) / year_funded_totals[y] for y in trend_years]
        ax.plot(trend_years, shares, marker="o", markersize=4, linewidth=2.25, color=trend_cmap(i), label=f)
    ax.set_xlabel("year")
    ax.set_ylabel("share of that year's funded studies (%)")

    def _avg_share(f, ys):
        vals = [100 * by_year_funder[f].get(y, 0) / year_funded_totals[y] for y in ys]
        return sum(vals) / len(vals) if vals else 0.0

    early_years = [y for y in trend_years if y <= 2016]
    late_years = [y for y in trend_years if y >= 2022]
    trend_deltas = {f: _avg_share(f, late_years) - _avg_share(f, early_years) for f in trend_funders}
    riser = max(trend_deltas, key=trend_deltas.get)
    faller = min(trend_deltas, key=trend_deltas.get)
    trend_headline = "The mix of top funders is shifting over time"
    trend_desc = "Each top funder's share of that year's studies with a known funder, 2013–2025."
    trend_finding = (f"{riser}'s share rose {trend_deltas[riser]:+.1f}pp from 2013–16 to 2022–25; "
                      f"{faller}'s {'rose' if trend_deltas[faller] >= 0 else 'fell'} "
                      f"{trend_deltas[faller]:+.1f}pp.")
    set_headline(ax, trend_headline, trend_desc, trend_finding, "fig_funder_trend.png")
    clean_axes(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False, fontsize=8.5)
    set_footnote(fig, f"Base: studies 2013–2025 with a known research funder (name-normalized); top "
                       f"{TOP_N_TREND} funders by total study count. 2026 excluded (partial year).")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_funder_trend.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_funder_authorship_alluvial: funder -> financing function -> authorship pattern ---
    # (needs Plotly's Sankey trace + kaleido, same pattern as fig_alluvial.png)
    primary_func_fa = {}
    for s, g in zip(function_j["s"], function_j["g"]):
        if s not in primary_func_fa:
            primary_func_fa[s] = FUNC_GRPS[g]

    fa_top_funders = set(fh_order[:6])
    fa_rows = []
    for s, keys in funders_of_s.items():
        if len(keys) != 1:
            continue
        funder = funder_display_name[next(iter(keys))]
        if funder not in fa_top_funders:
            continue
        cs = s_to_c_fp.get(s)
        if not cs or len(cs) != 1:
            continue
        ci = next(iter(cs))
        ac = author_countries_of_s.get(s)
        if ac is None:
            continue
        fn = primary_func_fa.get(s)
        if fn is None or fn == "Unclear":
            continue
        local_iso3 = iso3_of_c.get(ci)
        if ac == {local_iso3}:
            auth_cat = "Local authors only"
        elif local_iso3 in ac:
            auth_cat = "Local and foreign"
        else:
            auth_cat = "Foreign authors only"
        fa_rows.append((funder, fn, auth_cat))

    fa_funders = sorted({r[0] for r in fa_rows}, key=lambda f: -sum(1 for r in fa_rows if r[0] == f))
    fa_funcs = [f for f in ms_funcs if any(r[1] == f for r in fa_rows)]
    fa_auth_cats = ["Local authors only", "Local and foreign", "Foreign authors only"]

    fa_node_keys = ([("funder", f) for f in fa_funders] + [("func", f) for f in fa_funcs] +
                     [("auth", a) for a in fa_auth_cats])
    fa_idx_of = {k: i for i, k in enumerate(fa_node_keys)}
    fa_node_labels = [k[1] for k in fa_node_keys]
    fa_funder_palette = dict(zip(fa_funders,
        [ACCENT, GOLD, "#1baf7a", "#8a5fb0", "#c0392b", "#2a9d8f", "#e07b39", "#6b7280"]))
    fa_auth_palette = {"Local authors only": ACCENT, "Local and foreign": GREY, "Foreign authors only": "#e0752f"}

    fa_link1 = Counter((r[0], r[1]) for r in fa_rows)
    fa_link2 = Counter((r[1], r[2]) for r in fa_rows)
    fa_sources, fa_targets, fa_values, fa_colors = [], [], [], []
    for (f, fn), v in fa_link1.items():
        fa_sources.append(fa_idx_of[("funder", f)])
        fa_targets.append(fa_idx_of[("func", fn)])
        fa_values.append(v)
        fa_colors.append(fa_funder_palette.get(f, "#adb5bd"))
    for (fn, a), v in fa_link2.items():
        fa_sources.append(fa_idx_of[("func", fn)])
        fa_targets.append(fa_idx_of[("auth", a)])
        fa_values.append(v)
        fa_colors.append("rgba(150,150,150,0.35)")
    fa_node_colors = ([fa_funder_palette[f] for f in fa_funders] +
                       ["#5a6472"] * len(fa_funcs) +
                       [fa_auth_palette[a] for a in fa_auth_cats])

    fa_sankey_fig = go.Figure(go.Sankey(
        node=dict(label=[SHORT_FN.get(n, n) for n in fa_node_labels], color=fa_node_colors, pad=14,
                  thickness=14, line=dict(color="white", width=0.5)),
        link=dict(source=fa_sources, target=fa_targets, value=fa_values, color=fa_colors)))
    fa_sankey_fig.update_layout(width=1700, height=1000, margin=dict(l=10, r=10, t=10, b=10),
                                 paper_bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=INK))
    tmp_fa_sankey = FIGS / "_tmp_fig_funder_authorship_alluvial.png"
    fa_sankey_fig.write_image(str(tmp_fa_sankey), scale=2)

    top_funder_fa = fa_funders[0]
    top_funder_fa_n = sum(1 for r in fa_rows if r[0] == top_funder_fa)
    foreign_n_fa = sum(1 for r in fa_rows if r[2] == "Foreign authors only")
    fa_headline = "Funder-backed evidence flows through a few dominant pathways"
    fa_desc = ("Each ribbon is a group of single-funder, single-country studies flowing from research "
               "funder, through primary financing function, to authorship pattern.")
    fa_finding = (f"{top_funder_fa} funds the most studies in this flow ({top_funder_fa_n:,}), and "
                  f"{foreign_n_fa} of all {len(fa_rows):,} studies shown ({100 * foreign_n_fa / len(fa_rows):.0f}%) "
                  f"have no local author at all.")
    FIG_META["fig_funder_authorship_alluvial.png"] = (fa_headline, fa_desc, fa_finding)

    fig = plt.figure(figsize=(12, 8))
    ax_sk = fig.add_axes([0.02, 0.05, 0.96, 0.72])
    ax_sk.imshow(plt.imread(tmp_fa_sankey))
    ax_sk.axis("off")
    fig.text(0.02, 0.97, D(fa_headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.92, D(fa_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.885, D(fa_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top",
             wrap=True)
    fig.text(0.01, 0.02, f"Base: {len(fa_rows):,} single-country studies with exactly one recognized "
                         f"funder (among the top 6 by study count), a known author-affiliation country, "
                         f"and ≥1 financing-function tag (primary tag shown).", fontsize=7.6,
             color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.patch.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_funder_authorship_alluvial.png", dpi=150)
    plt.close(fig)
    tmp_fa_sankey.unlink(missing_ok=True)

# ---------------------------------------------------------------------------
# 11d. Country choropleth maps — real country geometry via Plotly+kaleido,
# mirroring HEE's fig_map_burden / fig_map_deserts / fig_map_growth /
# fig_worldmap.
# ---------------------------------------------------------------------------
if HAVE_PLOTLY:
    # --- fig_map_burden: research intensity vs. burden, continuous diverging ---
    studied_b = cdf_b.loc[cdf_b["studies"] > 0].copy()
    studied_b["log_per100k"] = np.log10(studied_b["per100k"].clip(lower=0.01))
    med_log = float(np.log10(studied_b["per100k"].median()))
    half_span = max(studied_b["log_per100k"].max() - med_log, med_log - studied_b["log_per100k"].min())
    build_continuous_map_figure(
        "fig_map_burden.png",
        "Research intensity against disease burden",
        "HFF studies naming each country, per 100,000 DALYs of disease burden. Blue: more research per "
        "unit of burden than the typical studied country; red: less.",
        f"The median studied country has {studied_b['per100k'].median():.2f} studies per 100,000 DALYs "
        f"— rich, small countries cluster far above that line, populous LMICs far below it.",
        f"Base: {len(studied_b):,} countries with GBD 2023 burden data and ≥1 study; global median "
        f"{studied_b['per100k'].median():.2f}. Grey = no study naming the country, or no GBD burden row.",
        studied_b["iso3"].tolist(), studied_b["log_per100k"].tolist(),
        ["#8c2d20", "#c0392b", "#f2ead9", "#5b78ab", "#2e4a72"],
        med_log - half_span, med_log + half_span,
        [med_log - half_span, med_log - half_span / 2, med_log, med_log + half_span / 2, med_log + half_span],
        ["low", "", "median", "", "high"], "studies per\n100k DALYs")

    # --- fig_map_deserts: binned study counts, flags zero-study countries ---
    def _desert_bucket(n):
        if n == 0:
            return 0
        if n <= 5:
            return 1
        if n <= 20:
            return 2
        return 3

    dfb_d = cdf_b.copy()
    dfb_d["bucket"] = dfb_d["studies"].apply(_desert_bucket)
    desert_palette = ["#c0392b", "#e8d9b5", "#8fbf9f", "#1f6d4a"]  # None, 1-5, 6-20, 21+
    n_deserts = int((dfb_d["bucket"] == 0).sum())
    desert_names = dfb_d.loc[dfb_d["bucket"] == 0, "country"].tolist()
    tmp_dm = FIGS / "_tmp_fig_map_deserts.png"
    render_discrete_map_png(dfb_d["iso3"].tolist(), dfb_d["bucket"].tolist(), desert_palette, tmp_dm)
    dm_headline = (f"{desert_names[0]} is the only country with disease burden but no HFF evidence at all"
                   if n_deserts == 1 else f"{n_deserts} countries carry disease burden but have no HFF "
                   f"evidence at all")
    dm_desc = ("Countries by number of HFF studies naming them, against the whole map of GBD 2023 burden. "
               "Red = a country that carries disease burden but has no HFF study at all.")
    dm_finding = (f"{desert_names[0]} has GBD burden data but zero HFF studies naming it." if n_deserts == 1
                  else f"{', '.join(desert_names[:5])} have GBD burden data but zero HFF studies naming them.")
    FIG_META["fig_map_deserts.png"] = (dm_headline, dm_desc, dm_finding)
    fig = plt.figure(figsize=(11, 8))
    ax_map = fig.add_axes([0.03, 0.10, 0.90, 0.62])
    ax_map.imshow(plt.imread(tmp_dm))
    ax_map.axis("off")
    ax_map.set_facecolor(PAPER)
    leg_labels = ["21+", "6–20", "1–5", "None"]
    leg_colors = [desert_palette[3], desert_palette[2], desert_palette[1], desert_palette[0]]
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in leg_colors]
    fig.legend(handles, leg_labels, loc="lower center", ncol=4, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, 0.02), title="HFF studies")
    fig.text(0.02, 0.975, D(dm_headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.925, D(dm_desc), fontsize=9.5, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.875, D(dm_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    fig.text(0.01, 0.10, f"Base: {len(dfb_d):,} countries with GBD 2023 burden data.",
             fontsize=7.6, color=SUBHEAD_COLOR, ha="left", va="bottom")
    fig.patch.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_map_deserts.png", dpi=150)
    plt.close(fig)
    tmp_dm.unlink(missing_ok=True)

    # --- fig_map_growth: share of a country's studies published 2018-2026 ---
    era_lv = LV["era"]
    era2018_code = era_lv.index("2018-2026")
    c_era_counts = defaultdict(lambda: [0, 0])
    for s, c in zip(geo_j["s"], geo_j["c"]):
        rec = c_era_counts[c]
        rec[1] += 1
        if studies["era"][s] == era2018_code:
            rec[0] += 1
    growth_rows = [(c, n2018 / ntot) for c, (n2018, ntot) in c_era_counts.items() if ntot >= 5]
    growth_isos = [countries[c]["iso3"] for c, _ in growth_rows]
    growth_vals = [v for _, v in growth_rows]
    global_avg_growth = 100 * sum(growth_vals) / len(growth_vals)
    build_continuous_map_figure(
        "fig_map_growth.png",
        "Where the HFF evidence is youngest",
        f"Share of a country's HFF studies published in 2018–2026, the later half of the window "
        f"(global average {global_avg_growth:.0f}%). Green = newer, faster-growing evidence base than "
        f"average; brown = older.",
        f"The evidence base is growing fastest in the Gulf and parts of Africa; several Latin American "
        f"and Eastern European countries still carry a majority pre-2018 evidence base.",
        f"Base: countries with ≥5 HFF studies, 2010–2026. Grey = fewer than 5 studies.",
        growth_isos, growth_vals,
        ["#7a5c3e", "#efe9da", "#2f8f5b"], 0.0, 1.0,
        [0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"], "% since 2018")

    # --- fig_worldmap: studies per 10M people, diverging red↔blue option ---
    wdf = cdf_b.loc[(cdf_b["studies"] > 0) & (cdf_b["pop"].notna())].copy()
    wdf["per10m"] = wdf["studies"] / (wdf["pop"] / 1e7)
    wdf["log_per10m"] = np.log10(wdf["per10m"].clip(lower=0.1))
    wmin, wmax = wdf["log_per10m"].min(), wdf["log_per10m"].max()
    build_continuous_map_figure(
        "fig_worldmap.png",
        "Where the HFF evidence is about",
        "HFF studies naming each country, per 10 million people (log scale), shown on a diverging red–blue scale.",
        f"North America, Western Europe, Australia and the Gulf are studied far more intensively per "
        f"capita than South Asia or sub-Saharan Africa — {wdf['per10m'].median():.1f} studies per 10M "
        f"people is the median.",
        f"Base: {len(wdf):,} countries with ≥1 study and population data. Grey = no study naming the "
        f"country. Population: World Bank.",
        wdf["iso3"].tolist(), wdf["log_per10m"].tolist(),
        ["#cc2f27", "#efe9da", "#2a5ea8"], wmin, wmax,
        [wmin, (wmin + wmax) / 2, wmax], ["low", "", "high"], "studies per\n10M people")

    # --- fig_map_method: modal type of analysis per country ---
    # HEE's version showed cost-utility (QALY) vs. cost-effectiveness; HFF has
    # no evaluation-type field, so this swaps in type_of_analysis (Quantitative
    # vs. Qualitative vs. Mixed methods) as the modal category.
    lv_toa_mm = LV["type_of_analysis"]
    country_toa_mm = defaultdict(Counter)
    for s, c in zip(geo_j["s"], geo_j["c"]):
        country_toa_mm[c][lv_toa_mm[studies["type_of_analysis"][s]]] += 1
    mm_modal = {}
    for c, cnt in country_toa_mm.items():
        if sum(cnt.values()) < 5:
            continue
        top_n = max(cnt.values())
        ties = [k for k, v in cnt.items() if v == top_n]
        mm_modal[c] = "Quantitative" if "Quantitative" in ties else ties[0]
    mm_cats = ["Quantitative", "Qualitative", "Mixed methods"]
    mm_cats = [c for c in mm_cats if c in set(mm_modal.values())] or sorted(set(mm_modal.values()))
    mm_palette = dict(zip(mm_cats, [ACCENT, "#1baf7a", GOLD]))
    mm_codes = {c: i for i, c in enumerate(mm_cats)}
    mm_isos = [countries[c]["iso3"] for c in mm_modal]
    mm_vals = [mm_codes[mm_modal[c]] for c in mm_modal]
    tmp_mm = FIGS / "_tmp_fig_map_method.png"
    render_discrete_map_png(mm_isos, mm_vals, [mm_palette[c] for c in mm_cats], tmp_mm)

    mm_counts = Counter(mm_modal.values())
    mm_top_cat, mm_top_n = mm_counts.most_common(1)[0]
    mm_headline = "Quantitative analysis dominates almost everywhere"
    mm_desc = ("The most common type of analysis among each country's HFF studies (≥5 studies). Colour "
               "is the modal category.")
    mm_finding = (f"{mm_top_cat} is the modal type in {mm_top_n} of {len(mm_modal)} countries with enough "
                  f"studies to classify — {'Qualitative' if 'Qualitative' in mm_counts else 'other types'} "
                  f"leads in only {len(mm_modal) - mm_top_n}.")
    FIG_META["fig_map_method.png"] = (mm_headline, mm_desc, mm_finding)

    fig = plt.figure(figsize=(11, 8))
    ax_map = fig.add_axes([0.03, 0.10, 0.90, 0.62])
    ax_map.imshow(plt.imread(tmp_mm))
    ax_map.axis("off")
    ax_map.set_facecolor(PAPER)
    handles_mm = [plt.Rectangle((0, 0), 1, 1, color=mm_palette[c]) for c in mm_cats]
    fig.legend(handles_mm, mm_cats, loc="lower center", ncol=len(mm_cats), frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, 0.02), title="Most common type")
    fig.text(0.02, 0.975, D(mm_headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.925, D(mm_desc), fontsize=9.5, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.885, D(mm_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top",
             wrap=True)
    fig.text(0.01, 0.10, f"Base: {len(mm_modal):,} countries with ≥5 HFF studies naming them.",
             fontsize=7.6, color=SUBHEAD_COLOR, ha="left", va="bottom")
    fig.patch.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_map_method.png", dpi=150)
    plt.close(fig)
    tmp_mm.unlink(missing_ok=True)

    # --- fig_map_authorship: share of a country's studies with a local author ---
    if have_authors:
        ma_rows = [(c, 100 * n[0] / n[1], n[1]) for c, n in local_by_country.items() if n[1] >= 5]
        ma_isos = [countries[c]["iso3"] for c, _, _ in ma_rows]
        ma_vals = [v for _, v, _ in ma_rows]
        most_external = min(ma_rows, key=lambda r: r[1])
        build_continuous_map_figure(
            "fig_map_authorship.png",
            "Who studies whom",
            "Share of a country's single-country HFF studies that have at least one author based there. "
            "Blue = mostly domestic; red = mostly produced from outside.",
            f"{countries[most_external[0]]['country']} has the lowest local-authorship share "
            f"({most_external[1]:.0f}%) among countries with ≥5 studies with a known affiliation.",
            f"Base: {sum(r[2] for r in ma_rows):,} single-country studies with a known author-affiliation "
            f"country, across {len(ma_rows)} countries with ≥5 such studies.",
            ma_isos, ma_vals,
            ["#c0392b", "#f2ead9", "#2a5ea8"], 0, 100,
            [0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"], "% with a\nlocal author")

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

# ---------------------------------------------------------------------------
# 13-14. Topic landscape: UMAP coords from docs/dex_hff/topic_map.csv (supplied
# separately — optional; no coordinate columns exist in the main extraction),
# but cluster labels/sizes now come from the v2 extraction's own
# topic_cluster_id/topic_cluster_label/topic_cluster_n columns instead of the
# old separate topic_labels.csv lookup file — same clustering (topic_cluster_id
# matches topic_map.csv's cluster column 1:1), but sourced from the file that's
# actually kept in sync with the pipeline, dropping one fragile external
# dependency.
# ---------------------------------------------------------------------------
have_topics = RAW_CSV.exists() and (DEX / "topic_map.csv").exists()
if have_topics:
    topic_map = pd.read_csv(DEX / "topic_map.csv")
    topic_map = topic_map[topic_map["record_id"].isin(ID_TO_IDX)].copy()

    tc_raw = pd.read_csv(RAW_CSV, usecols=["record_id", "topic_cluster_id", "topic_cluster_label",
                                            "topic_cluster_n"])
    tc_raw = tc_raw.dropna(subset=["topic_cluster_id"])
    tc_raw = tc_raw[tc_raw["topic_cluster_id"] != -1]
    tc_raw["topic_cluster_id"] = tc_raw["topic_cluster_id"].astype(int)
    topic_labels = (tc_raw.drop_duplicates("topic_cluster_id")
                     .set_index("topic_cluster_id")[["topic_cluster_n", "topic_cluster_label"]]
                     .rename(columns={"topic_cluster_n": "n", "topic_cluster_label": "label"}))
    topic_labels["n"] = topic_labels["n"].astype(int)

    N_TOP = 12
    ranked = topic_labels.sort_values("n", ascending=False)
    top_clusters = ranked.head(N_TOP).index.tolist()
    top_theme_label = ranked.iloc[0]["label"]
    top_theme_n = int(ranked.iloc[0]["n"])
    top_theme_share = round(100 * sum(ranked.head(N_TOP)["n"]) / ranked["n"].sum())
    cmap = plt.get_cmap("tab20")
    cluster_color = {c: cmap(i / max(N_TOP - 1, 1)) for i, c in enumerate(top_clusters)}

    other = topic_map[~topic_map["cluster"].isin(top_clusters)]
    fig, ax = plt.subplots(figsize=(9, 7.6))
    ax.scatter(other["x"], other["y"], s=3, color=GREY, alpha=0.35, linewidths=0, zorder=2,
               label=f"Other / unclustered ({len(other):,})")
    for c in top_clusters:
        sub = topic_map[topic_map["cluster"] == c]
        lbl = topic_labels.loc[c, "label"]
        ax.scatter(sub["x"], sub["y"], s=4, color=cluster_color[c], alpha=0.6, linewidths=0,
                   zorder=3, label=f"{lbl} ({len(sub):,})")
    set_headline(ax, "A handful of themes dominate the thematic landscape",
                 "Abstract embeddings, UMAP + HDBSCAN — each point is one study, positioned by similarity.",
                 f"'{top_theme_label}' is the largest emergent theme at {top_theme_n:,} studies; the top 12 "
                 f"themes shown here cover about {top_theme_share}% of all topic-embedded studies.",
                 "fig_topicmap.png")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False,
              markerscale=3, title=f"Top {N_TOP} themes")
    set_footnote(fig, f"Base: {len(topic_map):,} studies with a topic embedding. Position = 2D UMAP projection of "
                       f"sentence embeddings; colour = HDBSCAN cluster.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_topicmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    theme_counts = {row["label"]: row["n"] for _, row in ranked.head(20).iterrows()}
    second_theme_label = ranked.iloc[1]["label"]
    second_theme_n = int(ranked.iloc[1]["n"])
    hbar(theme_counts, "One emergent theme outranks all others",
         "Top 20 research themes, ranked by cluster size (keyword labels, not hand-assigned categories).",
         f"'{top_theme_label}' leads at {top_theme_n:,} studies, {round(top_theme_n / second_theme_n, 1)}× "
         f"the next-largest ('{second_theme_label}', {second_theme_n:,}).",
         "fig_theme_rank.png", f"Base: {int(topic_labels['n'].sum()):,} studies with a topic embedding, "
         f"across {len(topic_labels)} emergent themes.", color=GOLD, xlabel="records")

    # --- fig_topicmap_income: emergent theme map, coloured by LMIC share ---
    lv_scope_ti = LV["geo_scope"]
    single_code_ti = lv_scope_ti.index("Single country")
    s_to_c_ti = defaultdict(set)
    for s, c in zip(geo_j["s"], geo_j["c"]):
        s_to_c_ti[s].add(c)
    single_income_of_s = {}
    for s in range(N):
        if studies["geo_scope"][s] != single_code_ti:
            continue
        cs = s_to_c_ti.get(s)
        if cs and len(cs) == 1:
            inc = income_of_c.get(next(iter(cs)))
            if inc:
                single_income_of_s[s] = inc
    topic_map_ti = topic_map.copy()
    topic_map_ti["idx"] = topic_map_ti["record_id"].map(ID_TO_IDX)
    topic_map_ti["income"] = topic_map_ti["idx"].map(single_income_of_s)
    known_ti = topic_map_ti.dropna(subset=["income"])
    cluster_lmic_share = known_ti.groupby("cluster")["income"].apply(lambda s: (s != "High income").mean())
    overall_lmic_share = (known_ti["income"] != "High income").mean()

    ti_cmap = mcolors.LinearSegmentedColormap.from_list("ti", ["#2a5ea8", "#c9c3b3", "#e0752f"])
    ti_norm = mcolors.Normalize(vmin=0, vmax=1)
    point_lmic = topic_map_ti["cluster"].map(cluster_lmic_share)
    colored_pts = topic_map_ti[point_lmic.notna()]
    colored_vals = point_lmic[point_lmic.notna()]
    grey_pts = topic_map_ti[point_lmic.isna()]

    most_lmic_cluster = cluster_lmic_share.idxmax()
    most_hic_cluster = cluster_lmic_share.idxmin()
    most_lmic_label = topic_labels.loc[most_lmic_cluster, "label"]
    most_hic_label = topic_labels.loc[most_hic_cluster, "label"]

    fig, ax = plt.subplots(figsize=(9.5, 8))
    ax.scatter(grey_pts["x"], grey_pts["y"], s=3, color=GREY, alpha=0.25, linewidths=0, zorder=2)
    sc = ax.scatter(colored_pts["x"], colored_pts["y"], s=4, c=colored_vals, cmap=ti_cmap, norm=ti_norm,
                     alpha=0.7, linewidths=0, zorder=3)
    cb = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("share about LMICs", fontsize=9, color=SUBHEAD_COLOR)
    cb.ax.tick_params(labelsize=8)
    cb.outline.set_visible(False)
    set_headline(ax, "Research about poor and rich countries sits in different themes",
                 f"The emergent theme map, each theme coloured by the share of its single-country studies "
                 f"about LMICs (overall {overall_lmic_share:.0%}).",
                 f"'{most_lmic_label}' skews most LMIC ({cluster_lmic_share[most_lmic_cluster]:.0%}); "
                 f"'{most_hic_label}' skews most high-income "
                 f"({1 - cluster_lmic_share[most_hic_cluster]:.0%} high-income).",
                 "fig_topicmap_income.png")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    set_footnote(fig, f"Base: {len(known_ti):,} single-country studies with a known income group and a topic "
                       f"embedding, across {len(cluster_lmic_share)} emergent themes.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_topicmap_income.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

# ---------------------------------------------------------------------------
# 15. Topic landscape (OpenAlex-style taxonomy): a circular bar chart, one bar
# per subfield, grouped and coloured by field, from ml_thematic_cluster in the
# raw CSV (not in docs/data/, read directly and cheaply via usecols) — mirrors
# HEE's fig_topic_landscape.webp exactly (radial bars, not a sunburst).
# ---------------------------------------------------------------------------
have_taxonomy = RAW_CSV.exists()
if have_taxonomy:
    raw_tax = pd.read_csv(RAW_CSV, usecols=["record_id", "ml_thematic_cluster", "mesh_theme", "mesh_source"])
    raw_tax = raw_tax[raw_tax["record_id"].isin(ID_TO_IDX)]
    tax = raw_tax.dropna(subset=["ml_thematic_cluster"])
    parts = tax["ml_thematic_cluster"].str.split(" / ", n=2, expand=True)
    tax = tax.assign(domain=parts[0], field=parts[1], subfield=parts[2])
    n_tax = len(tax)

    field_domain = tax.groupby("field")["domain"].agg(lambda s: s.mode()[0])
    domain_totals = tax["domain"].value_counts()
    domain_order = domain_totals.index.tolist()
    domain_palette = dict(zip(
        domain_order,
        ["#2f6fb0", "#2a9d8f", "#67a65b", "#7c6ca8", "#cf6f61"],
    ))

    def topic_color(domain, value, max_value):
        """Use a shared domain hue, darkening smoothly with study count."""
        base = np.array(mcolors.to_rgb(domain_palette[domain]))
        weight = 0.56 + 0.40 * np.sqrt(value / max_value)
        return tuple(1 - (1 - base) * weight)

    N_BARS = 20
    subfield_counts = tax["subfield"].value_counts()
    subfield_field = tax.groupby("subfield")["field"].agg(lambda s: s.mode()[0])
    top_subfields = subfield_counts.head(N_BARS)
    # Group contiguously by domain (biggest domain first), then by field within
    # domain, then by count within field — matches HEE's clustered layout.
    bar_rows = list(reversed(list(top_subfields.items())))
    bar_labels = ["\n".join(textwrap.wrap(name, width=38, break_long_words=False))
                  for name, _ in bar_rows]
    bar_values = [n for _, n in bar_rows]
    bar_domains = [field_domain[subfield_field[name]] for name, _ in bar_rows]
    bar_colors = [topic_color(d, v, int(top_subfields.iloc[0]))
                  for d, v in zip(bar_domains, bar_values)]

    # bar_rows is sorted domain-then-field-then-count (for the chart's grouped
    # layout), NOT by count — the actual top subfield/domain come straight
    # from the count rankings instead.
    top_subfield, top_subfield_n = subfield_counts.index[0], int(subfield_counts.iloc[0])
    second_subfield, second_subfield_n = subfield_counts.index[1], int(subfield_counts.iloc[1])
    top_domain = domain_order[0]
    top_domain_n = int(domain_totals.iloc[0])
    headline = "One subfield dominates the topic taxonomy"
    desc = "OpenAlex-style topic taxonomy - the 20 largest subfields, coloured by domain."
    finding = (f"'{top_subfield}' leads at {top_subfield_n:,} studies, {round(top_subfield_n / second_subfield_n, 1)}× "
               f"the next-largest ('{second_subfield}', {second_subfield_n:,}); {top_domain} accounts for "
               f"{top_domain_n:,} of {n_tax:,} studies with a topic label.")
    FIG_META["fig_topic_landscape.png"] = (headline, desc, finding)

    fig, ax = plt.subplots(figsize=(12.8, 9.2))
    y = np.arange(len(bar_rows))
    ax.barh(y, bar_values, color=bar_colors, height=0.72, zorder=3)
    ax.set_yticks(y, bar_labels)
    ax.set_xlim(0, max(bar_values) * 1.16)
    value_pad = max(bar_values) * 0.012
    for row_y, value in zip(y, bar_values):
        ax.text(value + value_pad, row_y, f"{value:,}", va="center", ha="left",
                fontsize=8.8, color=INK, fontweight="bold")
    ax.set_xlabel("studies")
    ax.tick_params(axis="y", labelsize=8.8)
    clean_axes(ax)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    set_headline(ax, headline, desc, finding, "fig_topic_landscape.png")
    shown_domains = [d for d in domain_order if d in bar_domains]
    legend_handles = [plt.Rectangle((0, 0), 1, 1, color=domain_palette[d]) for d in shown_domains]
    ax.legend(legend_handles, shown_domains, loc="lower right", frameon=False,
              fontsize=8.8, ncol=2)
    set_footnote(fig, f"Base: {n_tax:,} studies with an ml_thematic_cluster label ({pct(n_tax, N)}% of the "
                       f"analysis population). Top {N_BARS} subfields shown; colour identifies domain and "
                       f"shade reflects study count.")
    fig.subplots_adjust(left=0.31, right=0.96, top=0.78, bottom=0.12)
    fig.savefig(FIGS / "fig_topic_landscape.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # -----------------------------------------------------------------------
    # 15a. Same topic taxonomy as a treemap. The circular bar chart above is
    # dominated by one subfield (Economics and Econometrics) that's over 2x
    # the next-largest — a real finding (financing-function research clusters
    # in generic economics/policy topics far more than clinical medicine
    # does), but bar-length encoding makes that one spoke look visually
    # broken next to HEE's more evenly-spread version. A treemap (area
    # encoding, ggplot2 treemapify-style) handles the same skewed
    # distribution gracefully — kept alongside the circular chart, not
    # instead of it.
    # -----------------------------------------------------------------------
    # A domain-nested treemap (outer rect per domain, subfields squarified
    # inside) degenerates into thin horizontal slivers here: with only 2
    # domains at meaningful scale (Social/Health Sciences, near-even split),
    # the outer partition is itself a wide, short band, and that bad aspect
    # ratio cascades into every subfield inside it. Two changes fix it:
    # (1) a single FLAT squarify pass over all subfields (color still marks
    # domain, just without a hard spatial boundary between them), which lets
    # the algorithm mix cell shapes freely instead of being constrained by a
    # bad parent rectangle; (2) area computed from sqrt(studies), not studies
    # directly — with the raw count, 'Economics and Econometrics' alone (32%
    # of the top-16 total) still forces most other cells into slivers. This
    # trades exact area-proportionality for legibility (disclosed in the
    # footnote); the circular chart above remains the linearly-accurate view.
    TM_N = 12
    tm_subfields = subfield_counts.head(TM_N)
    tm_items = [(name, int(n), field_domain[subfield_field[name]]) for name, n in tm_subfields.items()]
    tm_total = sum(n for _, n, _ in tm_items)

    TM_W, TM_H = 100.0, 62.0
    scaled = [n / tm_total * (TM_W * TM_H) for _, n, _ in tm_items]
    rects = squarify_treemap_balanced(scaled, 0, 0, TM_W, TM_H)

    tm_rects, tm_labels, tm_colors, tm_values = [], [], [], []
    for (name, v, d), r in zip(tm_items, rects):
        tm_rects.append(r)
        tm_labels.append(name)
        tm_colors.append(topic_color(d, v, top_subfield_n))
        tm_values.append(v)
    tm_domains = sorted({d for _, _, d in tm_items}, key=lambda d: -sum(n for _, n, dd in tm_items if dd == d))

    tm_headline = f"'{top_subfield}' alone accounts for a quarter of the topic taxonomy"
    tm_desc = ("Same OpenAlex-style topic taxonomy as the ranked chart, laid out as a treemap — "
               "each rectangle is a subfield (area = studies), grouped and coloured by field/domain.")
    tm_finding = (f"'{top_subfield}' is {round(top_subfield_n / n_tax * 100)}% of {n_tax:,} tagged "
                  f"studies on its own, {round(top_subfield_n / second_subfield_n, 1)}× the next-largest "
                  f"subfield ('{second_subfield}', {second_subfield_n:,}) — proportional area makes that "
                  f"concentration immediately visible.")
    FIG_META["fig_topic_landscape_treemap.png"] = (tm_headline, tm_desc, tm_finding)

    fig = plt.figure(figsize=(12.8, 8.6))
    ax = fig.add_axes([0.035, 0.155, 0.93, 0.585])
    for (x, y, w, h), color, label, v in zip(tm_rects, tm_colors, tm_labels, tm_values):
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.01,rounding_size=0.35",
            facecolor=color, edgecolor=PAPER, linewidth=1.8, zorder=3,
        )
        ax.add_patch(patch)
        if w * h > 95 and w > 7 and h > 6:
            wrap_width = max(10, min(30, int(w * 0.72)))
            wrapped = "\n".join(textwrap.wrap(label, width=wrap_width, break_long_words=False))
            fs = 10 if w * h > 450 else 8.2
            luminance = np.dot(np.array(color), [0.2126, 0.7152, 0.0722])
            text_color = "white" if luminance < 0.58 else INK
            txt = ax.text(x + w / 2, y + h / 2, f"{wrapped}\n{int(v):,}",
                          ha="center", va="center", fontsize=fs, color=text_color,
                          fontweight="bold", linespacing=1.18, zorder=4)
            txt.set_clip_path(patch)
    ax.set_xlim(0, TM_W)
    ax.set_ylim(0, TM_H)
    ax.invert_yaxis()
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.text(0.02, 0.975, D(tm_headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.925, D(tm_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.885, D(tm_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    legend_handles = [plt.Rectangle((0, 0), 1, 1, color=domain_palette[d]) for d in tm_domains]
    fig.legend(legend_handles, tm_domains, loc="lower center", ncol=len(tm_domains), frameon=False,
               fontsize=9.5, bbox_to_anchor=(0.5, 0.095))
    fig.text(0.01, 0.06, f"Base: top {TM_N} subfields by study count (of {n_tax:,} studies with an "
                         f"ml_thematic_cluster label). Cell area is directly proportional to study count; "
                         f"colour identifies the broader domain and shade reflects study count.",
             fontsize=8, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_topic_landscape_treemap.png", dpi=150)
    plt.close(fig)

    # -----------------------------------------------------------------------
    # 15b. Opportunity matrix: MeSH-derived disease category x financing
    # function. Mirrors HEE's fig_funder_opportunity.webp (disease area x
    # income group, research share ÷ GBD burden share) — HFF has no funder
    # field and no disease-burden data broken out by financing function, so
    # the two axes here are disease category x financing function, and the
    # reference/denominator is each function's own share across ALL
    # disease-tagged studies (not an external burden dataset).
    # -----------------------------------------------------------------------
    mesh_pop = raw_tax[(raw_tax["mesh_source"] == "pubmed") & raw_tax["mesh_theme"].notna()].copy()
    mesh_pop["disease_cat"] = mesh_pop["mesh_theme"].apply(classify_disease)
    mesh_pop = mesh_pop.dropna(subset=["disease_cat"])
    mesh_pop["idx"] = mesh_pop["record_id"].map(ID_TO_IDX)
    disease_of = dict(zip(mesh_pop["idx"], mesh_pop["disease_cat"]))
    disease_totals = Counter(mesh_pop["disease_cat"])

    dfc = {d: Counter() for d in disease_totals}
    opp_func_totals = Counter()
    for s, g in zip(function_j["s"], function_j["g"]):
        fn = FUNC_GRPS[g]
        if fn == "Unclear":
            continue
        d = disease_of.get(s)
        if d is None:
            continue
        dfc[d][fn] += 1
        opp_func_totals[fn] += 1

    n_disease_total = sum(disease_totals.values())
    opp_funcs = [fn for fn, _ in opp_func_totals.most_common()]
    overall_share = {fn: opp_func_totals[fn] / n_disease_total for fn in opp_funcs}

    CELL_MIN = 5

    def row_mean_ratio(d):
        vals = [(dfc[d][fn] / disease_totals[d]) / overall_share[fn]
                for fn in opp_funcs if dfc[d][fn] >= CELL_MIN]
        return sum(vals) / len(vals) if vals else float("inf")

    disease_order = sorted(disease_totals, key=row_mean_ratio)

    log_grid = np.full((len(disease_order), len(opp_funcs)), np.nan)
    count_grid = np.zeros_like(log_grid)
    for i, d in enumerate(disease_order):
        for j, fn in enumerate(opp_funcs):
            n = dfc[d][fn]
            count_grid[i, j] = n
            if n >= CELL_MIN:
                log_grid[i, j] = np.log2((n / disease_totals[d]) / overall_share[fn])

    flat = [(disease_order[i], opp_funcs[j], count_grid[i, j], log_grid[i, j])
            for i in range(len(disease_order)) for j in range(len(opp_funcs))
            if count_grid[i, j] >= CELL_MIN]
    most_under = min(flat, key=lambda t: t[3])
    most_over = max(flat, key=lambda t: t[3])
    n_pubmed_mesh = int((raw_tax["mesh_source"] == "pubmed").sum())
    pct_classified = pct(len(mesh_pop), n_pubmed_mesh)

    opp_headline = "Financing-function attention diverges sharply by disease area"
    opp_desc = ("For each MeSH-derived disease category, its share of tags for a given financing function, "
                "divided by that function's overall share across all disease-tagged studies. Blue = "
                "disproportionately more attention; red = disproportionately less.")
    opp_finding = (
        f"{most_over[0]} studies are tagged {SHORT_FN.get(most_over[1], most_over[1])} "
        f"{2 ** most_over[3]:.2g}× as often as the disease-tagged average, while {most_under[0]} studies "
        f"are tagged {SHORT_FN.get(most_under[1], most_under[1])} only {2 ** most_under[3]:.2g}× as often "
        f"— the widest gaps in either direction.")
    FIG_META["fig_funder_opportunity.png"] = (opp_headline, opp_desc, opp_finding)

    masked = np.ma.masked_invalid(log_grid)
    opp_cmap = mcolors.LinearSegmentedColormap.from_list(
        "opp", ["#8c2d20", "#c0392b", "#f2ead9", "#5b78ab", "#2e4a72"])
    opp_cmap.set_bad("#e5e1d6")
    opp_norm = mcolors.Normalize(vmin=-2, vmax=2)

    fig = plt.figure(figsize=(11, 9.4))
    ax = fig.add_axes([0.33, 0.27, 0.53, 0.53])
    im = ax.imshow(masked, cmap=opp_cmap, norm=opp_norm, aspect="auto")
    col_labels = [SHORT_FN.get(fn, fn).replace(": ", ":\n") for fn in opp_funcs]
    ax.set_xticks(range(len(opp_funcs)))
    ax.set_xticklabels(col_labels, fontsize=8, rotation=28, ha="right")
    ax.set_yticks(range(len(disease_order)))
    ax.set_yticklabels([f"{d}  (n={disease_totals[d]:,})" for d in disease_order], fontsize=9.5)
    for i, d in enumerate(disease_order):
        for j, fn in enumerate(opp_funcs):
            n = count_grid[i, j]
            if n < CELL_MIN:
                ax.text(j, i, f"n={int(n)}", ha="center", va="center", fontsize=7.5, color="#8a8272")
            else:
                ax.text(j, i, f"{2 ** log_grid[i, j]:.2g}×", ha="center", va="center",
                        fontsize=8.5, fontweight="bold", color=INK)
    ax.set_xticks(np.arange(-0.5, len(opp_funcs), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(disease_order), 1), minor=True)
    ax.grid(which="minor", color=PAPER, linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False, length=0)
    ax.tick_params(which="major", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    cbar_ax = fig.add_axes([0.90, 0.37, 0.02, 0.36])
    cb = fig.colorbar(im, cax=cbar_ax)
    cb.set_ticks([-2, -1, 0, 1, 2])
    cb.set_ticklabels(["0.25×", "0.5×", "matched", "2×", "4×"])
    cb.ax.tick_params(labelsize=8)
    cb.outline.set_visible(False)
    fig.text(0.90, 0.755, "tag share ÷\noverall share", fontsize=8, color=SUBHEAD_COLOR, ha="left", va="bottom")

    fig.text(0.02, 0.975, D(opp_headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.935, D(opp_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.895, D(opp_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    fig.text(0.01, 0.155,
             f"Disease category: PubMed-sourced MeSH terms only (not the OpenAlex-fallback theme), "
             f"keyword-matched to 11 broad groups modeled on HEE's MeSH C-tree groupings — "
             f"{pct_classified}% of {n_pubmed_mesh:,} PubMed-MeSH records matched a category "
             f"({n_disease_total:,} studies). Reference is each function's own share of this disease-tagged "
             f"subset, not GBD disease burden — HFF has no burden data by financing function, unlike "
             f"HEE's DALY-based opportunity matrix. Grey cells have <{CELL_MIN} studies for that pairing.",
             fontsize=7.6, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_funder_opportunity.png", dpi=150)
    plt.close(fig)

    # -----------------------------------------------------------------------
    # 15c. Disease-category cross-tabs. All reuse the MeSH-derived disease
    # classification (disease_of/disease_totals) computed above for the
    # opportunity matrix — same 7,031-study, PubMed-MeSH-only coverage.
    # -----------------------------------------------------------------------
    s_to_cs_disease = defaultdict(set)
    for s, c in zip(geo_j["s"], geo_j["c"]):
        s_to_cs_disease[s].add(c)
    disease_income = {d: Counter() for d in disease_totals}
    for s, d in disease_of.items():
        for c in s_to_cs_disease.get(s, ()):
            inc = income_of_c.get(c)
            if inc:
                disease_income[d][inc] += 1

    # --- fig_disease_method: how each disease area is evaluated (row %) ---
    dm_funcs = [fn for fn in FUNC_GRPS if fn != "Unclear"]
    dm_disease_order = sorted(disease_totals, key=lambda d: -disease_totals[d])
    dm_grid = np.array([[100 * dfc[d][fn] / disease_totals[d] for fn in dm_funcs] for d in dm_disease_order])
    dm_cmap = mcolors.LinearSegmentedColormap.from_list("dm", ["#eef5f5", "#4f8f96", "#123a40"])

    fig, ax = plt.subplots(figsize=(11, 7.6))
    im = ax.imshow(dm_grid, cmap=dm_cmap, aspect="auto", vmin=0, vmax=dm_grid.max())
    ax.set_xticks(range(len(dm_funcs)))
    ax.set_xticklabels([SHORT_FN.get(fn, fn).replace(": ", ":\n") for fn in dm_funcs], fontsize=8,
                        rotation=28, ha="right")
    ax.set_yticks(range(len(dm_disease_order)))
    ax.set_yticklabels(dm_disease_order, fontsize=9.5)
    for i in range(dm_grid.shape[0]):
        for j in range(dm_grid.shape[1]):
            v = dm_grid[i, j]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                    color="white" if v > dm_grid.max() * 0.55 else INK)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(bottom=False, left=False)
    dm_top_disease = dm_disease_order[np.argmax(dm_grid.max(axis=1))]
    dm_top_func = dm_funcs[int(np.argmax(dm_grid[dm_disease_order.index(dm_top_disease)]))]
    dm_top_val = dm_grid[dm_disease_order.index(dm_top_disease)].max()
    set_headline(ax, "How each disease area is evaluated",
                 "Mix of financing-function tags within each MeSH-derived disease category (row shares; a "
                 "study can carry more than one tag, so rows needn't sum to 100%).",
                 f"{dm_top_disease} leans hardest on {SHORT_FN.get(dm_top_func, dm_top_func)} "
                 f"({dm_top_val:.0f}% of its tagged studies).",
                 "fig_disease_method.png")
    clean_axes(ax)
    ax.grid(False)
    set_footnote(fig, f"Base: {sum(disease_totals.values()):,} PubMed-MeSH-classified studies across 11 disease "
                       f"categories (partial coverage of the corpus).")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_disease_method.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_disease_circular: disease share of literature, coloured by income skew ---
    fc_order = sorted(disease_totals, key=lambda d: -disease_totals[d])
    total_disease_all = sum(disease_totals.values())
    fc_shares = [100 * disease_totals[d] / total_disease_all for d in fc_order]
    fc_lmic = []
    for d in fc_order:
        cnt = disease_income[d]
        tot = sum(cnt.values())
        fc_lmic.append(100 * (tot - cnt.get("High income", 0)) / tot if tot else 50.0)
    skew_cmap = mcolors.LinearSegmentedColormap.from_list("skew", ["#2a5ea8", "#c9c3b3", "#e0752f"])
    skew_norm = mcolors.Normalize(vmin=0, vmax=100)
    fc_colors = [skew_cmap(skew_norm(v)) for v in fc_lmic]

    n_fc = len(fc_order)
    gap_fc = np.radians(3.0)
    slot_fc = (2 * np.pi - gap_fc * n_fc) / n_fc
    theta_fc = [i * (slot_fc + gap_fc) + slot_fc / 2 for i in range(n_fc)]

    top_lmic_i = int(np.argmax(fc_lmic))
    top_hic_i = int(np.argmin(fc_lmic))
    fcirc_headline = "The disease focus of HFF research"
    fcirc_desc = ("Each bar is a MeSH-derived disease category; length is its share of the disease-coded "
                  "literature, colour is whether that research skews toward richer or poorer countries.")
    fcirc_finding = (f"{fc_order[top_lmic_i]} research skews most toward LMICs ({fc_lmic[top_lmic_i]:.0f}% "
                      f"LMIC); {fc_order[top_hic_i]} skews most toward high-income settings "
                      f"({100 - fc_lmic[top_hic_i]:.0f}% high-income).")
    FIG_META["fig_disease_circular.png"] = (fcirc_headline, fcirc_desc, fcirc_finding)

    fig = plt.figure(figsize=(10, 9.3))
    ax = fig.add_axes([0.1, 0.16, 0.8, 0.68], projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    # Increase the inner hole and narrow the wedges so the centre label has more breathing room and the bars look less crowded.
    inner_r_fc = max(fc_shares) * 0.52
    ax.bar(theta_fc, fc_shares, width=slot_fc * 0.64, bottom=inner_r_fc, color=fc_colors,
           edgecolor=PAPER, linewidth=0.6, zorder=3)
    # Add a solid inner disc in the background colour to keep the centre clean.
    ax.bar([0], [inner_r_fc * 0.99], width=2 * np.pi, bottom=0,
           color=PAPER, edgecolor=PAPER, linewidth=0, align="edge", zorder=4)
    for t, v, name in zip(theta_fc, fc_shares, fc_order):
        deg = np.degrees(t)
        ha = "left" if deg < 180 else "right"
        ax.text(t, inner_r_fc + v + max(fc_shares) * 0.10, f"{name} {v:.0f}%",
                rotation=90 - deg if deg < 180 else 270 - deg, rotation_mode="anchor",
                ha=ha, va="center", fontsize=9, color=INK)
    ax.text(0, 0, f"{total_disease_all:,}\nstudies", ha="center", va="center", fontsize=12,
            fontweight="bold", color=INK, transform=ax.transData, zorder=5,
            bbox=dict(boxstyle="circle,pad=1.0", facecolor=PAPER, edgecolor="none"))
    ax.set_ylim(0, inner_r_fc + max(fc_shares) * 1.72)
    ax.set_xticks([]); ax.set_yticks([])
    ax.spines["polar"].set_visible(False)
    ax.grid(False)

    leg_ax = fig.add_axes([0.35, 0.075, 0.3, 0.02])
    grad = np.linspace(0, 100, 256).reshape(1, -1)
    leg_ax.imshow(grad, aspect="auto", cmap=skew_cmap, norm=skew_norm, extent=[0, 1, 0, 1])
    leg_ax.set_xticks([0, 0.5, 1])
    leg_ax.set_xticklabels(["Skews\nhigh-income", "Balanced", "Skews\nLMIC"], fontsize=8, color=INK)
    leg_ax.set_yticks([])
    for spine in leg_ax.spines.values():
        spine.set_visible(False)

    fig.text(0.02, 0.975, D(fcirc_headline), fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.93, D(fcirc_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.885, D(fcirc_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top",
             wrap=True)
    fig.text(0.5, 0.025, f"Base: {total_disease_all:,} PubMed-MeSH-classified studies across 11 disease "
                         f"categories (partial coverage of the corpus).",
             fontsize=7.6, color=SUBHEAD_COLOR, ha="center", va="top")
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_disease_circular.png", dpi=150)
    plt.close(fig)

    # --- fig_transition: LMIC research mix across 3 epi-transition classes ---
    COMM_GROUP = {"Infectious", "Maternal & neonatal"}
    INJ_GROUP = {"Injuries"}
    lmic_c_idx = {i for i, inc in income_of_c.items() if inc and inc != "High income"}
    trans_by_year = defaultdict(Counter)
    for s, d in disease_of.items():
        if not any(c in lmic_c_idx for c in s_to_cs_disease.get(s, ())):
            continue
        y = studies["year"][s]
        if y == 2026:
            continue
        grp = ("Communicable, maternal & nutritional" if d in COMM_GROUP
               else "Injuries" if d in INJ_GROUP else "Non-communicable")
        trans_by_year[y][grp] += 1
    trans_years = sorted(trans_by_year)
    trans_groups = ["Communicable, maternal & nutritional", "Non-communicable", "Injuries"]
    trans_colors = {"Communicable, maternal & nutritional": "#c0392b", "Non-communicable": ACCENT,
                     "Injuries": GREY}
    trans_series = {g: [] for g in trans_groups}
    for y in trans_years:
        tot_y = sum(trans_by_year[y].values())
        for g in trans_groups:
            trans_series[g].append(100 * trans_by_year[y].get(g, 0) / tot_y if tot_y else None)

    fig, ax = plt.subplots(figsize=(9, 5.6))
    for g in trans_groups:
        ax.plot(trans_years, trans_series[g], color=trans_colors[g], linewidth=2.5, marker="o",
                 markersize=4, label=g, zorder=3)
    comm_first, comm_last = trans_series["Communicable, maternal & nutritional"][0], \
        trans_series["Communicable, maternal & nutritional"][-1]
    ncd_first, ncd_last = trans_series["Non-communicable"][0], trans_series["Non-communicable"][-1]
    set_headline(ax, "LMIC research has shifted from communicable disease toward NCDs",
                 "Disease mix of MeSH-classified HFF research about low- and middle-income countries, across "
                 "three epidemiological-transition classes.",
                 f"Communicable/maternal/nutritional fell {comm_first:.0f}%→{comm_last:.0f}%; "
                 f"non-communicable rose {ncd_first:.0f}%→{ncd_last:.0f}%, {trans_years[0]}–"
                 f"{trans_years[-1]}.",
                 "fig_transition.png")
    ax.set_ylabel("share of LMIC MeSH-classified research (%)")
    ax.set_ylim(0, 100)
    ax.set_xlim(min(trans_years) - 0.5, max(trans_years) + 0.5)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
    clean_axes(ax)
    ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
    ax.legend(loc="center left", frameon=False, fontsize=9)
    set_footnote(fig, f"Base: {sum(sum(c.values()) for c in trans_by_year.values()):,} MeSH-classified studies "
                       f"about LMIC countries, by year. No disease-specific burden data exists to benchmark "
                       f"against (unlike HEE's version) — shown as research composition only.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_transition.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_alluvial: study design -> financing function -> outcome domain ---
    # (needs Plotly's Sankey trace + kaleido, same as the map figures above)
    primary_func = {}
    for s, g in zip(function_j["s"], function_j["g"]):
        if s not in primary_func:
            primary_func[s] = FUNC_GRPS[g]
    primary_outcome = {}
    for s, g in zip(outcome_j["s"], outcome_j["g"]):
        if s not in primary_outcome:
            primary_outcome[s] = OUTCOME_GRPS[g]
    design_lv = LV["study_design"]
    raw_sankey_rows = []
    for s in range(N):
        if s not in primary_func or s not in primary_outcome:
            continue
        d = design_lv[studies["study_design"][s]]
        f = primary_func[s]
        o = primary_outcome[s]
        if "Unclear" in (d, f, o):
            continue
        raw_sankey_rows.append((d, f, o))

    # Cap the study-design stage to the top categories (there are 13; HEE's
    # own version only had ~5) so node labels don't overlap; the rest fold
    # into "Other designs".
    TOP_DESIGNS = 7
    design_counts_a = Counter(r[0] for r in raw_sankey_rows)
    top_design_names = {d for d, _ in design_counts_a.most_common(TOP_DESIGNS)}
    sankey_rows = [(d if d in top_design_names else "Other designs", f, o) for d, f, o in raw_sankey_rows]

    design_list = sorted({r[0] for r in sankey_rows}, key=lambda dd: -sum(1 for r in sankey_rows if r[0] == dd))
    func_list = [f for f in FUNC_GRPS if f != "Unclear"]
    out_list = [o for o in OUTCOME_GRPS if o != "Unclear"]
    # Node keys are (stage, label) tuples, NOT bare labels — "Other" exists in
    # both financing_function_grps and outcome_domain_grps, and a plain
    # label->index dict would silently collapse those into one node.
    node_keys = ([("design", d) for d in design_list] + [("func", f) for f in func_list] +
                 [("out", o) for o in out_list])
    idx_of = {k: i for i, k in enumerate(node_keys)}
    node_labels = [k[1] for k in node_keys]
    design_palette_sk = dict(zip(design_list, [
        "#2f6fb0", "#2a9d8f", "#5aa9b8", "#7c6ca8",
        "#4d8c74", "#7a9cc6", "#8aa6a3", "#6f7f92",
    ]))
    outcome_palette_sk = dict(zip(out_list, [
        "#315f8c", "#397f8b", "#4f9c8c", "#6aa7a3", "#718db8",
        "#806fa5", "#9a7fa8", "#5e7b73", "#7d8f9d", "#a1adb7",
    ]))

    def sankey_rgba(hex_color, alpha):
        red, green, blue = [round(channel * 255) for channel in mcolors.to_rgb(hex_color)]
        return f"rgba({red},{green},{blue},{alpha})"

    link1 = Counter((r[0], r[1]) for r in sankey_rows)
    link2 = Counter((r[1], r[2]) for r in sankey_rows)
    sk_sources, sk_targets, sk_values, sk_colors = [], [], [], []
    for (d, f), v in link1.items():
        sk_sources.append(idx_of[("design", d)]); sk_targets.append(idx_of[("func", f)]); sk_values.append(v)
        sk_colors.append(sankey_rgba(design_palette_sk.get(d, "#8aa6a3"), 0.34))
    for (f, o), v in link2.items():
        sk_sources.append(idx_of[("func", f)]); sk_targets.append(idx_of[("out", o)]); sk_values.append(v)
        sk_colors.append(sankey_rgba(FUNCTION_COLORS.get(f, "#7a9cc6"), 0.28))
    node_colors_sk = ([design_palette_sk[d] for d in design_list] +
                       [FUNCTION_COLORS.get(f, "#7a9cc6") for f in func_list] +
                       [outcome_palette_sk.get(o, "#7d8f9d") for o in out_list])

    sankey_fig = go.Figure(go.Sankey(
        node=dict(label=[SHORT_FN.get(n, n) for n in node_labels], color=node_colors_sk, pad=14, thickness=14,
                  line=dict(color="white", width=0.5)),
        link=dict(source=sk_sources, target=sk_targets, value=sk_values, color=sk_colors)))
    sankey_fig.update_layout(width=1700, height=1300, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=INK))
    tmp_sankey = FIGS / "_tmp_fig_alluvial.png"
    sankey_fig.write_image(str(tmp_sankey), scale=2)

    top_design_a = design_list[0]
    top_func_a, top_func_a_n = Counter(r[1] for r in sankey_rows).most_common(1)[0]
    top_outcome_a, top_outcome_a_n = Counter(r[2] for r in sankey_rows).most_common(1)[0]
    al_headline = "The evidence flows through a few dominant pathways"
    al_desc = ("Each ribbon is a group of studies flowing from study design, through primary financing "
               "function, to primary outcome domain (first-listed tag of each). Ribbon width is the study "
               "count.")
    al_finding = (f"{SHORT_FN.get(top_func_a, top_func_a)} is the largest single financing-function node "
                  f"({top_func_a_n:,} studies), feeding most often into {top_outcome_a} "
                  f"({top_outcome_a_n:,} studies primarily reporting it).")
    FIG_META["fig_alluvial.png"] = (al_headline, al_desc, al_finding)

    fig = plt.figure(figsize=(13, 9.5))
    # Sankey image previously stopped at height 0.66 while the header block
    # only reached down to ~0.87, leaving a large dead gap between them; give
    # it the rest of the canvas instead.
    ax_sk = fig.add_axes([0.02, 0.02, 0.96, 0.80])
    ax_sk.imshow(plt.imread(tmp_sankey), aspect="auto")
    ax_sk.axis("off")
    ax_sk.set_facecolor(PAPER)
    fig.text(0.02, 0.975, D(al_headline), fontsize=16, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.92, D(al_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.885, D(al_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top",
             wrap=True)
    fig.text(0.01, 0.02, f"Base: {len(sankey_rows):,} studies with a study design, a financing function and "
                         f"an outcome domain classified.", fontsize=8, color=SUBHEAD_COLOR, ha="left",
             va="bottom")
    fig.patch.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_alluvial.png", dpi=150)
    plt.close(fig)
    tmp_sankey.unlink(missing_ok=True)

    # --- fig_map_disease: small multiples, one choropleth per disease category ---
    disease_country_counts = {d: Counter() for d in disease_totals}
    for s, d in disease_of.items():
        for c in s_to_cs_disease.get(s, ()):
            disease_country_counts[d][c] += 1
    dmap_order = sorted(disease_totals, key=lambda d: -disease_totals[d])
    all_dmap_vals = [v for d in dmap_order for v in disease_country_counts[d].values()]
    dmap_vmax = float(np.log10(max(all_dmap_vals)))

    # One combined figure with 11 choropleth subplots -> a SINGLE write_image()
    # call, instead of 11 separate kaleido launches in a tight loop (which
    # crashes the headless-Chrome process pool under rapid repeated calls).
    from plotly.subplots import make_subplots
    ncols_dm = 3
    nrows_dm = -(-len(dmap_order) // ncols_dm)
    specs_dm = [[{"type": "choropleth"} for _ in range(ncols_dm)] for _ in range(nrows_dm)]
    tiles_fig = make_subplots(rows=nrows_dm, cols=ncols_dm, specs=specs_dm,
                               subplot_titles=dmap_order, horizontal_spacing=0.02, vertical_spacing=0.05)
    for i, d in enumerate(dmap_order):
        r, c_ = divmod(i, ncols_dm)
        cnt = disease_country_counts[d]
        isos = [countries[c]["iso3"] for c in cnt]
        zvals = [float(np.log10(v)) for v in cnt.values()]
        is_last = (i == len(dmap_order) - 1)
        tiles_fig.add_trace(go.Choropleth(
            locations=isos, locationmode="ISO-3", z=zvals, zmin=0, zmax=dmap_vmax,
            colorscale=[[0, "#eef2f5"], [1, "#1b3a5c"]], showscale=is_last,
            colorbar=dict(title="studies", tickvals=[0, dmap_vmax], ticktext=["1", f"{int(10 ** dmap_vmax):,}"],
                           len=0.5, thickness=15) if is_last else None,
            marker_line_color="white", marker_line_width=0.2), row=r + 1, col=c_ + 1)
    tiles_fig.update_geos(projection_type="robinson", showframe=False, showcoastlines=False,
                           landcolor="#e5e1d6", bgcolor="rgba(0,0,0,0)", showcountries=False,
                           center=dict(lon=0, lat=0), projection_rotation=dict(lon=0, lat=0))
    tiles_fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                             plot_bgcolor="rgba(0,0,0,0)", width=1500, height=1700,
                             font=dict(color=INK, size=13))
    tmp_dmap = FIGS / "_tmp_map_disease.png"
    tiles_fig.write_image(str(tmp_dmap), scale=2)

    md_headline = "The disease atlas"
    md_desc = "HFF studies naming each country, split by MeSH-derived disease area (busiest first). Log scale."
    md_finding = (f"'{dmap_order[0]}' research reaches the widest set of countries "
                  f"({len(disease_country_counts[dmap_order[0]])} named); several disease areas stay "
                  f"concentrated in a handful of systems.")
    FIG_META["fig_map_disease.png"] = (md_headline, md_desc, md_finding)

    fig = plt.figure(figsize=(12, 14))
    ax_grid = fig.add_axes([0.02, 0.03, 0.96, 0.85])
    ax_grid.imshow(plt.imread(tmp_dmap))
    ax_grid.axis("off")
    ax_grid.set_facecolor(PAPER)

    fig.text(0.02, 0.975, D(md_headline), fontsize=17, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.945, D(md_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.92, D(md_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top",
             wrap=True)
    fig.text(0.01, 0.012, f"Base: {sum(disease_totals.values()):,} PubMed-MeSH-classified studies across 11 "
                          f"disease categories (partial coverage of the corpus; see README). Robinson "
                          f"projection.", fontsize=7.6, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.patch.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_map_disease.png", dpi=150)
    plt.close(fig)
    tmp_dmap.unlink(missing_ok=True)

    # -------------------------------------------------------------------
    # fig_funder_trajectory: LMIC research share of each disease area,
    # era 1 -> era 2. HEE's original plots each disease area's LMIC
    # research-to-burden RATIO across two eras; HFF has no disease-
    # category-level GBD burden data (only country-level totals), so this
    # substitutes each category's LMIC SHARE of research directly — same
    # dumbbell/arrow "closing vs stuck" design, without a burden
    # denominator. Reuses disease_of/disease_totals/s_to_cs_disease from
    # the opportunity matrix and disease cross-tabs above.
    # -------------------------------------------------------------------
    era_lv_tj = LV["era"]
    era1_code = era_lv_tj.index("2010-2017")
    era2_code = era_lv_tj.index("2018-2026")
    disease_income_era = {d: {era1_code: Counter(), era2_code: Counter()} for d in disease_totals}
    for s, d in disease_of.items():
        e = studies["era"][s]
        if e not in (era1_code, era2_code):
            continue
        for c in s_to_cs_disease.get(s, ()):
            inc = income_of_c.get(c)
            if inc:
                disease_income_era[d][e][inc] += 1

    def _lmic_share_n(cnt):
        tot = sum(cnt.values())
        return (100 * (tot - cnt.get("High income", 0)) / tot, tot) if tot else (None, 0)

    traj_rows = []
    for d in disease_totals:
        s1, n1 = _lmic_share_n(disease_income_era[d][era1_code])
        s2, n2 = _lmic_share_n(disease_income_era[d][era2_code])
        if s1 is None or s2 is None:
            continue
        traj_rows.append((d, s1, s2, n1, n2))
    traj_rows.sort(key=lambda r: -r[2])

    biggest_gain = max(traj_rows, key=lambda r: r[2] - r[1])
    biggest_drop = min(traj_rows, key=lambda r: r[2] - r[1])
    min_n = min(min(r[3], r[4]) for r in traj_rows)

    fig, ax = plt.subplots(figsize=(10.5, 7.8))
    ys = list(range(len(traj_rows)))[::-1]
    for y, (d, s1, s2, n1, n2) in zip(ys, traj_rows):
        color = "#2e7d5b" if s2 >= s1 else "#c0392b"
        ax.plot([s1], [y], marker="o", color=GREY, markersize=6, zorder=3)
        ax.annotate("", xy=(s2, y), xytext=(s1, y), zorder=4,
                    arrowprops=dict(arrowstyle="-|>", color=color, linewidth=2.5, mutation_scale=16))
    ax.set_yticks(ys, [d for d, *_ in traj_rows], fontsize=9.5)
    ax.set_xlabel("share of research about LMICs (%)")
    ax.set_xlim(-3, 75)
    legend_handles = [
        plt.Line2D([0], [0], color="#2e7d5b", linewidth=2.5, marker=">", markersize=7,
                   label="Gaining LMIC share"),
        plt.Line2D([0], [0], color="#c0392b", linewidth=2.5, marker=">", markersize=7,
                   label="Losing LMIC share"),
    ]
    ax.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=2, frameon=False, fontsize=9.5)
    tj_headline = "LMIC research share is rising for most disease areas"
    tj_desc = ("Share of research about LMICs within each MeSH-derived disease category, "
               "2010–2017 (dot) to 2018–2026 (arrowhead).")
    tj_finding = (f"{biggest_gain[0]}'s LMIC share rose {biggest_gain[2] - biggest_gain[1]:+.0f}pp; "
                  f"{biggest_drop[0]}'s fell {biggest_drop[2] - biggest_drop[1]:+.0f}pp — the widest "
                  f"swings either way.")
    set_headline(ax, tj_headline, tj_desc, tj_finding, "fig_funder_trajectory.png")
    clean_axes(ax)
    ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
    set_footnote(fig, f"Base: PubMed-MeSH-classified, geo-tagged studies with a known country income group, "
                       f"split by era (2010–2017 vs. 2018–2026); smallest category has {min_n} "
                       f"studies in one era — read narrow categories with caution. HFF has no disease-"
                       f"category burden data, unlike HEE's burden-ratio design; this shows LMIC research "
                       f"share directly, not a ratio to burden.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_funder_trajectory.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

# ---------------------------------------------------------------------------
# 16-19. Global financing context (IHME "Financing Global Health 2025" data,
# docs/dex_hff/F*.xlsx — optional, real-world backdrop for the Revenue Raising
# financing function: development assistance for health (DAH) trends, the
# 2024->2025 aid cuts, and health-spending inequality by income group.
# ---------------------------------------------------------------------------
have_ihme = (DEX / "F03_Total_DAH_forecast_1990-2030.xlsx").exists()
if have_ihme:
    STATUS_STYLE = {"Historical": "-", "Preliminary": "-", "Forecast": (0, (4, 3))}

    # --- 16. Total DAH 1990-2030, historical + preliminary + forecast ---
    dah = pd.read_excel(DEX / "F03_Total_DAH_forecast_1990-2030.xlsx", sheet_name="in")
    dah = dah[["Year", "Development assistance for Health (DAH)", "Status"]].dropna()
    dah = dah.sort_values("Year")
    peak_row = dah.loc[dah["Development assistance for Health (DAH)"].idxmax()]
    peak_year, peak_val = int(peak_row["Year"]), peak_row["Development assistance for Health (DAH)"]
    latest = dah[dah["Status"] != "Forecast"].iloc[-1]
    latest_year, latest_val = int(latest["Year"]), latest["Development assistance for Health (DAH)"]
    drop_pct = round(100 * (1 - latest_val / peak_val), 0)

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for status in ["Historical", "Preliminary", "Forecast"]:
        seg = dah[dah["Status"] == status]
        if status == "Preliminary":
            prev = dah[dah["Status"] == "Historical"]
            seg = pd.concat([prev.tail(1), seg])
        elif status == "Forecast":
            prev = dah[dah["Status"] == "Preliminary"]
            seg = pd.concat([prev.tail(1), seg])
        ax.plot(seg["Year"], seg["Development assistance for Health (DAH)"], color=ACCENT,
                linewidth=2.75, linestyle=STATUS_STYLE[status], zorder=3,
                marker="o" if status == "Preliminary" else None, markersize=6)
    ax.axvline(peak_year, color="#8a8272", linewidth=0.8, linestyle=":", zorder=2)
    ax.annotate(f"{peak_year} peak: ${peak_val:,.0f}bn\n(COVID-19 response)", xy=(peak_year, peak_val),
                xytext=(peak_year - 8, peak_val - 5), fontsize=9, color=INK, fontweight="bold")
    set_headline(ax, "Global health aid has fallen off a cliff since its COVID-era peak",
                 "Development assistance for health (DAH), 1990–2030 — solid is historical/preliminary, dashed is forecast.",
                 f"DAH fell {drop_pct:.0f}% from its {peak_year} peak (${peak_val:,.0f}bn) to "
                 f"${latest_val:,.0f}bn in {latest_year}, and is forecast to stay flat through 2030.",
                 "fig_dah_trend.png")
    ax.set_ylabel("DAH (2023 USD, billions)")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=9))
    clean_axes(ax)
    ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
    ax.set_ylim(0, peak_val * 1.15)
    set_footnote(fig, "Base: IHME Financing Global Health 2025. 2025 is preliminary; 2026–2030 is forecast.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_dah_trend.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 17. 2024->2025 change by source: who drove the cut ---
    src = pd.read_excel(DEX / "F07_DAH_by_source_change_2024-2025.xlsx", sheet_name="in")
    src = src[["Source", "Difference_2024_to_2025", "Percent_change_2024_to_2025"]].dropna()
    src = src.sort_values("Difference_2024_to_2025")
    top_cutter = src.iloc[0]
    total_cut = src["Difference_2024_to_2025"].sum() / 1000  # millions -> billions
    colors = ["#c0392b" if v < 0 else "#1baf7a" for v in src["Difference_2024_to_2025"]]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    span = float(src["Difference_2024_to_2025"].abs().max()) / 1000
    ax.barh(src["Source"], src["Difference_2024_to_2025"] / 1000, color=colors, zorder=3)
    for y, (v, p) in enumerate(zip(src["Difference_2024_to_2025"] / 1000, src["Percent_change_2024_to_2025"])):
        offset = span * 0.02
        ax.text(offset if v >= 0 else -offset, y, f"{v:+,.1f}bn ({p:+.0f}%)",
                va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK)
    ax.axvline(0, color="#8a8272", linewidth=0.8, zorder=2)
    ax.set_xlim(-span * 1.28, span * 1.05)
    set_headline(ax, "The United States drove the 2025 aid collapse",
                 "Change in development assistance for health by source, 2024 → 2025.",
                 f"The US cut ${abs(top_cutter['Difference_2024_to_2025'] / 1000):,.1f}bn "
                 f"({top_cutter['Percent_change_2024_to_2025']:.0f}%) — alone larger than the "
                 f"${abs(total_cut):,.1f}bn net drop across all sources combined.",
                 "fig_dah_cuts_source.png")
    ax.set_xlabel("change in DAH, 2023 USD billions")
    clean_axes(ax)
    ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
    set_footnote(fig, "Base: IHME Financing Global Health 2025, DAH by source, 2023 USD millions converted to billions.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_dah_cuts_source.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 18. Health spending per person by income group, 2000-2030 ---
    hsp = pd.read_excel(DEX / "F11_Total_health_spending_per_person_by_WB_income_group_2000-2030.xlsx", sheet_name="in")
    hsp = hsp[["Year", "World Bank income group", "Total health spending per person", "Status"]].dropna()
    inc_order_hsp = ["High", "Upper-Middle", "Lower-Middle", "Low"]
    inc_colors_hsp = dict(zip(inc_order_hsp, [ACCENT, "#1baf7a", GOLD, "#c0392b"]))
    high_2025 = hsp[(hsp["World Bank income group"] == "High") & (hsp["Year"] == 2025)]["Total health spending per person"].iloc[0]
    low_2025 = hsp[(hsp["World Bank income group"] == "Low") & (hsp["Year"] == 2025)]["Total health spending per person"].iloc[0]
    low_2020 = hsp[(hsp["World Bank income group"] == "Low") & (hsp["Year"] == 2020)]["Total health spending per person"].iloc[0]
    gap_ratio = round(high_2025 / low_2025)

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for grp in inc_order_hsp:
        sub = hsp[hsp["World Bank income group"] == grp].sort_values("Year")
        hist = sub[sub["Status"] == "Historical"]
        fcst = sub[sub["Status"] != "Historical"]
        fcst = pd.concat([hist.tail(1), fcst])
        ax.plot(hist["Year"], hist["Total health spending per person"], color=inc_colors_hsp[grp],
                linewidth=2.5, zorder=3, label=grp)
        ax.plot(fcst["Year"], fcst["Total health spending per person"], color=inc_colors_hsp[grp],
                linewidth=2.5, linestyle=(0, (4, 3)), zorder=3)
    ax.set_yscale("log")
    set_headline(ax, "The health-spending gap between rich and poor countries keeps widening",
                 "Total health spending per person by World Bank income group, 2000–2030 (log scale; dashed = forecast).",
                 f"By 2025, the average person in a high-income country has ${high_2025:,.0f} spent on their "
                 f"health — {gap_ratio}× the ${low_2025:,.0f} in a low-income country, where per-person "
                 f"spending has fallen since 2020 (${low_2020:,.0f}).",
                 "fig_health_spending_income.png")
    ax.set_ylabel("health spending per person (2023 USD, log scale)")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    clean_axes(ax)
    # "upper left" sat on top of the High/Upper-Middle lines themselves (they
    # start high on this log scale); put the legend below the chart instead.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, frameon=False, fontsize=9)
    set_footnote(fig, "Base: IHME Financing Global Health 2025, health spending per person by World Bank income "
                       "group. 2025–2030 are forecast.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_health_spending_income.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 19. Cross-reference: our own Revenue Raising research volume vs. real DAH ---
    rr_idx = FUNC_GRPS.index("Revenue Raising")
    rr_years = Counter()
    for s, g in zip(function_j["s"], function_j["g"]):
        if g == rr_idx:
            rr_years[year_of_study[s]] += 1
    rr_common_years = sorted(y for y in rr_years if y in set(dah["Year"]) and y <= latest_year)
    rr_series = [rr_years.get(y, 0) for y in rr_common_years]
    dah_series = [dah.loc[dah["Year"] == y, "Development assistance for Health (DAH)"].iloc[0] for y in rr_common_years]
    corr = float(np.corrcoef(rr_series, dah_series)[0, 1]) if len(rr_series) > 2 else float("nan")

    rel = "tracks" if corr > 0.3 else ("moves opposite to" if corr < -0.3 else "does not clearly track")
    headline = ("Research on revenue raising has risen and fallen in step with real-world aid" if corr > 0.3
                else "Research on revenue raising has decoupled from real-world aid")
    desc = f"Studies tagged Revenue Raising per year (this dataset) vs. global DAH (IHME), {rr_common_years[0]}–{latest_year}."
    finding = (f"Revenue-Raising research volume {rel} the real DAH trend (correlation r={corr:.2f}) — "
               f"both rose through the 2010s and have pulled back since the DAH peak.")
    FIG_META["fig_revenue_vs_dah.png"] = (headline, desc, finding)

    fig = plt.figure(figsize=(9.5, 6.2))
    ax1 = fig.add_axes([0.09, 0.1, 0.78, 0.6])
    ax2 = ax1.twinx()
    l1, = ax1.plot(rr_common_years, rr_series, color=ACCENT, linewidth=2.75, marker="o", markersize=4, zorder=3)
    l2, = ax2.plot(rr_common_years, dah_series, color=GOLD, linewidth=2.25, linestyle=(0, (4, 3)), zorder=3)
    ax1.set_ylabel("Revenue Raising studies per year", color=ACCENT)
    ax2.set_ylabel("Global DAH (2023 USD, billions)", color=GOLD)
    ax1.tick_params(axis="y", labelcolor=ACCENT)
    ax2.tick_params(axis="y", labelcolor=GOLD)
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
    for spine in ("top",):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    ax1.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
    ax1.legend([l1, l2], ["Revenue Raising studies (left)", "Global DAH, $bn (right)"],
               loc="upper left", frameon=False, fontsize=9)
    fig.text(0.02, 0.975, D(headline), fontsize=14.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.90, D(desc), fontsize=10.5, color=SUBHEAD_COLOR, ha="left", va="top")
    fig.text(0.02, 0.85, D(finding), fontsize=10.5, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    fig.text(0.01, 0.02, f"Base: {sum(rr_series):,} Revenue-Raising-tagged studies, {rr_common_years[0]}–"
                          f"{rr_common_years[-1]}, vs. IHME DAH for the same years.",
             fontsize=8.5, color=SUBHEAD_COLOR, ha="left", va="bottom")
    fig.patch.set_facecolor(PAPER)
    ax1.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_revenue_vs_dah.png", dpi=150)
    plt.close(fig)

    # --- 20. Every financing function's growth index vs. DAH's growth index ---
    common_years = sorted(y for y in set(year_of_study) if y in set(dah["Year"]) and y <= latest_year and y >= 2010)
    base_years = common_years[:2]
    func_year_counts = {fn: Counter() for fn in FUNC_GRPS}
    for s, g in zip(function_j["s"], function_j["g"]):
        func_year_counts[FUNC_GRPS[g]][year_of_study[s]] += 1
    top6 = [k for k, _ in func_counts.most_common(6)]
    dah_by_year = dict(zip(dah["Year"], dah["Development assistance for Health (DAH)"]))
    dah_base = np.mean([dah_by_year[y] for y in base_years])
    dah_index = [100 * dah_by_year[y] / dah_base for y in common_years]

    fig, ax = plt.subplots(figsize=(9, 5.6))
    func_palette = [ACCENT, "#1baf7a", "#8a5fb0", "#c0392b", "#2a9d8f", "#e07b39"]
    best_fn, best_corr = None, -2
    for fn, col in zip(top6, func_palette):
        series = [func_year_counts[fn].get(y, 0) for y in common_years]
        base = np.mean(series[:2]) or 1
        index = [100 * v / base for v in series]
        r = float(np.corrcoef(index, dah_index)[0, 1])
        if r > best_corr:
            best_corr, best_fn = r, fn
        ax.plot(common_years, index, color=col, linewidth=2, zorder=3, label=SHORT_FN.get(fn, fn))
    ax.plot(common_years, dah_index, color=INK, linewidth=3, linestyle=(0, (4, 3)), zorder=4, label="Global DAH (IHME)")
    set_headline(ax, f"{best_fn}'s research volume tracks real-world aid most closely of any function",
                 f"Growth index ({base_years[0]}–{base_years[1]}=100) for the 6 largest financing "
                 f"functions' study counts, vs. global DAH, {common_years[0]}–{common_years[-1]}.",
                 f"{best_fn} correlates with the DAH trend at r={best_corr:.2f}, the closest match among the "
                 f"6 largest financing functions.",
                 "fig_functions_vs_dah_index.png")
    ax.set_ylabel(f"index ({base_years[0]}–{base_years[1]} = 100)")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=8))
    clean_axes(ax)
    ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False, fontsize=8.5)
    set_footnote(fig, f"Base: financing-function tags by publication year, {common_years[0]}–{common_years[-1]}, "
                       f"vs. IHME DAH for the same years. Each series indexed to its own {base_years[0]}–"
                       f"{base_years[1]} average.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_functions_vs_dah_index.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 21. Aid vs. evidence, by region (approximates GBD super-regions using
    # income group first, then UN region — not IHME's exact country list) ---
    def gbd_bucket(income, un_region):
        if income == "High income":
            return "High-income"
        return {
            "Sub-Saharan Africa": "Sub-Saharan Africa",
            "Southern Asia": "South Asia",
            "Eastern Asia": "Southeast Asia, East Asia, and Oceania",
            "South-eastern Asia": "Southeast Asia, East Asia, and Oceania",
            "Melanesia": "Southeast Asia, East Asia, and Oceania",
            "Northern Africa": "North Africa and Middle East",
            "Western Asia": "North Africa and Middle East",
            "Latin America and the Caribbean": "Latin America and Caribbean",
            "Eastern Europe": "Central Europe, Eastern Europe, and Central Asia",
            "Central Asia": "Central Europe, Eastern Europe, and Central Asia",
        }.get(un_region, "High-income")

    country_bucket = {i: gbd_bucket(c["income"], c["un_region"]) for i, c in enumerate(countries)}
    research_by_bucket = Counter(country_bucket[c] for c in geo_j["c"])
    research_total = sum(research_by_bucket.values())

    f04 = pd.read_excel(DEX / "F04_DAH_by_GBD_super-region_forecast_2015-2030.xlsx", sheet_name="in")
    f04 = f04[["Year", "Super-region", "Development assistance for health (DAH) received", "Status"]].dropna()
    aid_by_bucket = f04[f04["Year"].isin([2022, 2023, 2024])].groupby("Super-region")[
        "Development assistance for health (DAH) received"].mean()
    aid_total = aid_by_bucket.sum()

    buckets = sorted(set(aid_by_bucket.index) | set(research_by_bucket.keys()),
                      key=lambda b: -aid_by_bucket.get(b, 0))
    aid_share = [100 * aid_by_bucket.get(b, 0) / aid_total for b in buckets]
    research_share = [100 * research_by_bucket.get(b, 0) / research_total for b in buckets]
    gap = {b: r - a for b, a, r in zip(buckets, aid_share, research_share)}
    most_under = min(gap, key=gap.get)

    y_pos = np.arange(len(buckets))
    fig_h_in = 6.6
    fig, ax = plt.subplots(figsize=(10.5, fig_h_in))
    bar_h = 0.42
    ax.barh(y_pos - bar_h / 2 - 0.015, aid_share, height=bar_h, color=GOLD, zorder=3,
            label="Share of DAH (2022–24 avg)")
    ax.barh(y_pos + bar_h / 2 + 0.015, research_share, height=bar_h, color=ACCENT, zorder=3,
            label="Share of study-country pairs")
    ax.set_yticks(y_pos, buckets, fontsize=11)
    ax.invert_yaxis()

    av_headline = f"{most_under} gets a far larger share of aid than of research attention"
    av_desc = ("Share of global DAH (2022–24 average) vs. share of this dataset's study-country pairs, "
               "by region (income-first approximation of GBD super-regions).")
    av_finding = (f"{most_under} receives {aid_by_bucket.get(most_under, 0) / aid_total * 100:.0f}% of DAH but only "
                  f"{research_by_bucket.get(most_under, 0) / research_total * 100:.0f}% of study-country pairs — "
                  f"the largest aid-to-evidence gap of any region.")
    FIG_META["fig_aid_vs_evidence_region.png"] = (av_headline, av_desc, av_finding)

    ax.set_xlabel("share (%)")
    clean_axes(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2, frameon=False, fontsize=9.5)
    set_footnote(fig, "Base: IHME DAH by GBD super-region (F04) vs. this dataset's study-country pairs, bucketed "
                       "by World Bank income group (High income → ‘High-income’) then UN region — "
                       "an approximation of IHME's super-regions, not their exact country list.")
    fig.tight_layout()

    # Headline/desc/finding are long enough to look better wrapped across a
    # couple of lines instead of one line stretched the full figure width;
    # place them from the true left edge (fig-fraction, not axes-fraction) so
    # they also fill the blank space above the region labels, and size the
    # gap between each block from its *actual* wrapped line count so nothing
    # collides regardless of how many lines textwrap produces.
    def _line_frac(fontsize, linespacing, n_lines):
        return (fontsize * linespacing * n_lines) / (fig_h_in * 72)

    headline_lines = textwrap.wrap(av_headline, width=46, break_long_words=False)
    desc_lines = textwrap.wrap(av_desc, width=74, break_long_words=False)
    finding_lines = textwrap.wrap(av_finding, width=74, break_long_words=False)

    y = 0.975
    fig.text(0.02, y, D("\n".join(headline_lines)), fontsize=16, fontweight="bold", color=INK,
              ha="left", va="top", linespacing=1.25)
    y -= _line_frac(16, 1.25, len(headline_lines)) + 0.03

    fig.text(0.02, y, D("\n".join(desc_lines)), fontsize=10.5, color=SUBHEAD_COLOR,
              ha="left", va="top", linespacing=1.3)
    y -= _line_frac(10.5, 1.3, len(desc_lines)) + 0.025

    fig.text(0.02, y, D("\n".join(finding_lines)), fontsize=10.5, fontweight="bold", color=INK,
              ha="left", va="top", linespacing=1.3)
    y -= _line_frac(10.5, 1.3, len(finding_lines)) + 0.03

    fig.subplots_adjust(top=y)
    fig.savefig(FIGS / "fig_aid_vs_evidence_region.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 22. Research intensity vs. health spending per person, by country ---
    f12 = pd.read_excel(DEX / "F12_Total_health_spending_per_person_by_country_2025.xlsx", sheet_name="in")
    f12 = f12[["Location", "Total health spending per person"]].dropna()

    F12_ALIASES = {
        "united states of america": "United States of America", "russian federation": "Russia",
        "viet nam": "Vietnam", "lao people's democratic republic": "Laos",
        "bolivia (plurinational state of)": "Bolivia", "venezuela (bolivarian republic of)": "Venezuela",
        "iran (islamic republic of)": "Iran", "syrian arab republic": "Syria",
        "republic of korea": "South Korea", "democratic people's republic of korea": "North Korea",
        "republic of moldova": "Moldova", "brunei darussalam": "Brunei",
        "united republic of tanzania": "United Republic of Tanzania", "cote d'ivoire": "Ivory Coast",
        "czechia": "Czechia", "türkiye": "Turkey", "turkiye": "Turkey",
        "eswatini": "eSwatini", "north macedonia": "North Macedonia", "serbia": "Republic of Serbia",
        "timor-leste": "East Timor", "myanmar": "Myanmar", "hong kong special administrative region of china": "Hong Kong S.A.R.",
        "congo": "Republic of the Congo", "democratic republic of the congo": "Democratic Republic of the Congo",
        "micronesia (federated states of)": None, "united kingdom of great britain and northern ireland": "United Kingdom",
    }
    name_lookup_bc = {c["country"].lower(): c["country"] for c in countries}
    matched_rows = []
    for _, row in f12.iterrows():
        key = row["Location"].strip().lower()
        name = F12_ALIASES.get(key, name_lookup_bc.get(key))
        if name and name in name_lookup_bc.values():
            matched_rows.append((name, row["Total health spending per person"]))
    spend_by_country = dict(matched_rows)

    country_idx = {c["country"]: i for i, c in enumerate(countries)}
    study_counts_c = Counter(geo_j["c"])
    pts = []
    for name, spend in spend_by_country.items():
        i = country_idx[name]
        n_studies = study_counts_c.get(i, 0)
        pop = countries[i]["pop"]
        if n_studies > 0 and pop:
            pts.append((name, spend, 1e6 * n_studies / pop, countries[i]["income"]))

    inc_colors_pt = dict(zip(dict_json["meta"]["inc_lv"], dict_json["meta"]["pal_inc"]))
    fig, ax = plt.subplots(figsize=(8.5, 6))
    for inc in dict_json["meta"]["inc_lv"]:
        sub = [p for p in pts if p[3] == inc]
        if not sub:
            continue
        ax.scatter([p[1] for p in sub], [p[2] for p in sub], color=inc_colors_pt[inc], s=45, alpha=0.8,
                   edgecolors="white", linewidths=0.5, zorder=3, label=inc)
    ax.set_xscale("log")
    ax.set_yscale("log")
    log_spend = np.log10([p[1] for p in pts])
    log_studies = np.log10([p[2] for p in pts])
    corr_sp = float(np.corrcoef(log_spend, log_studies)[0, 1])
    set_headline(ax, "Research intensity rises with health spending per person",
                 "Studies per million people vs. health spending per person (2025), by country.",
                 f"Log-log correlation r={corr_sp:.2f} across {len(pts)} matched countries — richer-spending "
                 f"countries are studied far more intensively per capita.",
                 "fig_research_vs_spending_country.png")
    ax.set_xlabel("health spending per person, 2023 USD (log)")
    ax.set_ylabel("studies per million people (log)")
    clean_axes(ax)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    set_footnote(fig, f"Base: {len(pts)} countries matched between IHME health spending per person (F12, 2025) "
                       f"and this dataset's study-country pairs + World Bank population.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_research_vs_spending_country.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_funder_scorecard_expenditure: funder scorecard's burden/intensity
    # scatter + ranked deficit bar, re-run with total national health
    # expenditure (F12 per-person spending x population) standing in for GBD
    # disease burden. Structurally mirrors fig_funder_scorecard.png, but the
    # left panel's y-axis is studies per 100,000 PEOPLE (not per 100,000 of
    # the x-axis denominator) since "per 100,000 dollars" is meaningless at
    # national-expenditure scale — so the shaded zone/reference line use the
    # median rate as a descriptive split, not a strict proportionality claim
    # the way the burden version's line is. The right panel's deficit is
    # still a strict proportional-to-expenditure calculation, in absolute
    # study counts, exactly like the burden version.
    exp_rows = []
    for name, spend in spend_by_country.items():
        i = country_idx[name]
        pop = countries[i]["pop"]
        if not pop:
            continue
        exp_rows.append({"country": name, "income": countries[i]["income"], "pop": pop,
                          "total_exp": spend * pop, "studies": study_counts_c.get(i, 0)})
    exp_b = pd.DataFrame(exp_rows)
    exp_b["per100k"] = exp_b["studies"] / (exp_b["pop"] / 1e5)
    TOTAL_EXP_ALL = exp_b["total_exp"].sum()
    TOTAL_STUDIES_EXP = exp_b["studies"].sum()
    exp_b["expected"] = TOTAL_STUDIES_EXP * exp_b["total_exp"] / TOTAL_EXP_ALL
    exp_b["deficit"] = exp_b["studies"] - exp_b["expected"]
    exp_pts = exp_b[exp_b["studies"] > 0].copy()
    biggest_deficit_exp = exp_b.loc[exp_b["deficit"].idxmin()]

    TOP_N_DEFICIT_EXP = 15
    top_deficit_exp = exp_b.nsmallest(TOP_N_DEFICIT_EXP, "deficit").sort_values("deficit", ascending=False)
    fig = plt.figure(figsize=(13.5, 7.4))
    ax1 = fig.add_axes([0.055, 0.12, 0.44, 0.58])
    for inc in INC_ORDER:
        sub = exp_pts[exp_pts["income"] == inc]
        ax1.scatter(sub["total_exp"], sub["per100k"].clip(lower=0.005), s=(sub["pop"] / 3.5e5).clip(lower=12),
                    color=INC_COLORS[inc], alpha=0.75, edgecolors="white", linewidths=0.4, zorder=3)
    ax1.set_xscale("log")
    ax1.set_yscale("log")

    median_rate_exp = exp_pts["per100k"].median()
    x_min_exp, x_max_exp = exp_pts["total_exp"].min() * 0.8, exp_pts["total_exp"].max() * 1.3
    y_min_exp, y_max_exp = exp_pts["per100k"].clip(lower=0.005).min() * 0.7, exp_pts["per100k"].max() * 1.4
    ax1.set_xlim(x_min_exp, x_max_exp)
    ax1.set_ylim(y_min_exp, y_max_exp)
    zone_x0_exp = exp_pts["total_exp"].median()
    ax1.axhline(median_rate_exp, color="#8a8272", linewidth=1, linestyle=(0, (4, 3)), zorder=2)
    ax1.add_patch(plt.Rectangle((zone_x0_exp, y_min_exp), x_max_exp - zone_x0_exp, median_rate_exp - y_min_exp,
                                 facecolor="#c0392b", alpha=0.08, edgecolor="none", zorder=1))
    zone_text_exp = "priority zone\nhigh spending, low research intensity"
    zone_tx_exp, zone_ty_exp = zone_x0_exp * 2.2, y_min_exp * 2.6
    ax1.text(zone_tx_exp, zone_ty_exp, zone_text_exp,
             ha="left", va="center", fontsize=8.5, fontweight="bold", color="#a13a2a", linespacing=1.4)

    label_rows_exp = exp_pts[exp_pts["country"].isin(top_deficit_exp["country"])].sort_values("total_exp")
    declutter_labels(ax1, label_rows_exp, "total_exp", "per100k", name_map=SHORT_COUNTRY,
                      avoid=[(zone_tx_exp, zone_ty_exp, "left", zone_text_exp)])

    ax1.set_xlabel("Total health expenditure, 2023 USD (log)")
    ax1.set_ylabel("Studies per 100,000 people (log)")
    clean_axes(ax1)

    ax2 = fig.add_axes([0.58, 0.12, 0.4, 0.58])
    ax2.barh([SHORT_COUNTRY.get(c, c) for c in top_deficit_exp["country"]], -top_deficit_exp["deficit"],
             color=[INC_COLORS.get(i, GREY) for i in top_deficit_exp["income"]], zorder=3)
    for y, v in enumerate(-top_deficit_exp["deficit"]):
        ax2.text(v, y, f" +{v:,.0f}", va="center", fontsize=8.5, color=INK)
    ax2.set_xlabel("studies short of a spending-proportional share")
    ax2.set_title(f"The {TOP_N_DEFICIT_EXP} largest evidence deficits", fontsize=11, fontweight="bold",
                  color=INK, loc="left")
    clean_axes(ax2)

    sce_headline = "Funding priority scorecard: health expenditure edition"
    sce_desc = (f"Where research is most sparse relative to health spending (left, shaded), and the "
                f"{TOP_N_DEFICIT_EXP} countries with the largest absolute shortfall (right).")
    sce_finding = (f"{biggest_deficit_exp['country']} alone is {abs(round(biggest_deficit_exp['deficit'])):,} "
                   f"studies short of a spending-proportional share — the largest gap of any country.")
    FIG_META["fig_funder_scorecard_expenditure.png"] = (sce_headline, sce_desc, sce_finding)
    fig.text(0.02, 0.965, D(sce_headline.upper()), fontsize=17, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.915, D(sce_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.882, D(sce_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    income_legend(fig, loc="upper left", ncol=4, bbox_to_anchor=(0.02, 0.80))
    fig.text(0.01, 0.03, f"Base: {len(exp_b):,} countries matched between IHME health spending per person × "
                         f"World Bank population (F12, 2025) and this dataset's study-country pairs. Point "
                         f"area ∝ population. Expected = studies × (country expenditure ÷ total expenditure). "
                         f"Priority zone/reference line use the median rate as a descriptive split, not a "
                         f"proportionality claim (unlike the disease-burden scorecard). This flags countries "
                         f"under-studied relative to money spent, not necessarily neglected relative to need — "
                         f"so, unlike the disease-burden scorecard, high-spending wealthy countries can top "
                         f"this list alongside (or instead of) under-resourced ones.",
             fontsize=8, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.patch.set_facecolor(PAPER)
    ax1.set_facecolor(PAPER)
    ax2.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_funder_scorecard_expenditure.png", dpi=150)
    plt.close(fig)

    # --- fig_funder_scorecard_combined: all three at once — disease burden vs.
    # total health expenditure (so the reference line reads as "spent in
    # proportion to burden"), with bubble size now standing in for research
    # volume (studies) instead of population, so an under-spending country
    # that's ALSO barely studied shows up as a small bubble sitting well
    # below the line. The right panel's deficit uses a "need index" =
    # burden share ÷ spending share, so a country's expected research share
    # accounts for both how sick it is and how little it can spend, at once.
    combo_rows = []
    for name, spend in spend_by_country.items():
        i = country_idx[name]
        pop = countries[i]["pop"]
        dalys = countries[i].get("dalys")
        if not pop or dalys is None or (isinstance(dalys, float) and np.isnan(dalys)):
            continue
        combo_rows.append({"country": name, "income": countries[i]["income"], "pop": pop,
                            "dalys": dalys, "total_exp": spend * pop, "studies": study_counts_c.get(i, 0)})
    combo_b = pd.DataFrame(combo_rows)
    TOTAL_DALYS_COMBO = combo_b["dalys"].sum()
    TOTAL_EXP_COMBO = combo_b["total_exp"].sum()
    TOTAL_STUDIES_COMBO = combo_b["studies"].sum()
    combo_b["need_index"] = (combo_b["dalys"] / TOTAL_DALYS_COMBO) / (combo_b["total_exp"] / TOTAL_EXP_COMBO)
    combo_b["expected"] = TOTAL_STUDIES_COMBO * combo_b["need_index"] / combo_b["need_index"].sum()
    combo_b["deficit"] = combo_b["studies"] - combo_b["expected"]
    combo_pts = combo_b.copy()
    biggest_deficit_combo = combo_b.loc[combo_b["deficit"].idxmin()]

    TOP_N_DEFICIT_COMBO = 15
    top_deficit_combo = combo_b.nsmallest(TOP_N_DEFICIT_COMBO, "deficit").sort_values("deficit", ascending=False)
    fig = plt.figure(figsize=(13.5, 7.4))
    ax1 = fig.add_axes([0.055, 0.12, 0.44, 0.58])
    for inc in INC_ORDER:
        sub = combo_pts[combo_pts["income"] == inc]
        ax1.scatter(sub["dalys"], sub["total_exp"], s=(sub["studies"] * 0.3).clip(lower=8),
                    color=INC_COLORS[inc], alpha=0.75, edgecolors="white", linewidths=0.4, zorder=3)
    ax1.set_xscale("log")
    ax1.set_yscale("log")

    # A 1.3x margin is nowhere near enough headroom for the top bubble here:
    # bubble RADIUS is in fixed points, but log-scale margin is multiplicative,
    # and the largest bubble (by study count, e.g. the US) can be ~35-40pt in
    # radius against a top margin worth only a few points at 1.3x — enough
    # to visibly clip it. Use a much larger multiplier so the margin in
    # points comfortably exceeds any bubble's radius.
    x_min_combo, x_max_combo = combo_pts["dalys"].min() * 0.8, combo_pts["dalys"].max() * 1.8
    y_min_combo, y_max_combo = combo_pts["total_exp"].min() * 0.5, combo_pts["total_exp"].max() * 5.5
    ax1.set_xlim(x_min_combo, x_max_combo)
    ax1.set_ylim(y_min_combo, y_max_combo)
    k_combo = TOTAL_EXP_COMBO / TOTAL_DALYS_COMBO
    xs_line_combo = np.array([x_min_combo, x_max_combo])
    ys_line_combo = xs_line_combo * k_combo
    ax1.plot(xs_line_combo, ys_line_combo, color="#8a8272", linewidth=1, linestyle=(0, (4, 3)), zorder=2)
    ax1.fill_between(xs_line_combo, [y_min_combo, y_min_combo], ys_line_combo,
                      color="#c0392b", alpha=0.08, zorder=1)
    # Position in log-space (not a plain fraction of the linear x-range, which
    # would sit almost at x_max on a log axis) and left-align well short of
    # the right edge — a long, centered line here previously ran past ax1's
    # boundary and got sliced off by ax2's opaque background next to it.
    zone_text_combo = "priority zone\nunderfunded relative to its burden"
    log_zone_x_combo = np.log10(x_min_combo) + 0.40 * (np.log10(x_max_combo) - np.log10(x_min_combo))
    zone_tx_combo = 10 ** log_zone_x_combo
    zone_ty_combo = zone_tx_combo * k_combo * 0.3
    ax1.text(zone_tx_combo, zone_ty_combo, zone_text_combo,
             ha="left", va="center", fontsize=8.2, fontweight="bold", color="#a13a2a", linespacing=1.4)

    label_rows_combo = combo_pts[combo_pts["country"].isin(top_deficit_combo["country"])].sort_values("dalys")
    declutter_labels(ax1, label_rows_combo, "dalys", "total_exp", name_map=SHORT_COUNTRY,
                      avoid=[(zone_tx_combo, zone_ty_combo, "left", zone_text_combo)])

    ax1.set_xlabel("Disease burden (DALYs, 2023, log)")
    ax1.set_ylabel("Total health expenditure, 2023 USD (log)")
    clean_axes(ax1)

    ax2 = fig.add_axes([0.58, 0.12, 0.4, 0.58])
    ax2.barh([SHORT_COUNTRY.get(c, c) for c in top_deficit_combo["country"]], -top_deficit_combo["deficit"],
             color=[INC_COLORS.get(i, GREY) for i in top_deficit_combo["income"]], zorder=3)
    for y, v in enumerate(-top_deficit_combo["deficit"]):
        ax2.text(v, y, f" +{v:,.0f}", va="center", fontsize=8.5, color=INK)
    ax2.set_xlabel("studies short of a need-proportional share")
    ax2.set_title(f"The {TOP_N_DEFICIT_COMBO} largest evidence deficits", fontsize=11, fontweight="bold",
                  color=INK, loc="left")
    clean_axes(ax2)

    scc_headline = "Funding priority scorecard: burden, spending and research together"
    scc_desc = (f"Disease burden vs. total health expenditure (left, shaded below the burden-proportional "
                f"spending line); bubble size is each country's number of HFF studies, so a small bubble "
                f"below the line is both underfunded and understudied. The {TOP_N_DEFICIT_COMBO} countries "
                f"with the largest shortfall once burden AND spending capacity are both counted (right).")
    scc_finding = (f"{biggest_deficit_combo['country']} alone is {abs(round(biggest_deficit_combo['deficit'])):,} "
                   f"studies short of a share proportional to its burden-to-spending need — the largest gap "
                   f"of any country.")
    FIG_META["fig_funder_scorecard_combined.png"] = (scc_headline, scc_desc, scc_finding)
    fig.text(0.02, 0.965, D(scc_headline.upper()), fontsize=17, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.915, D(scc_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.865, D(scc_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    income_legend(fig, loc="upper left", ncol=4, bbox_to_anchor=(0.02, 0.80))
    fig.text(0.01, 0.03, f"Base: {len(combo_b):,} countries matched across GBD 2023 DALYs, IHME health spending "
                         f"per person × World Bank population (F12, 2025), and this dataset's study-country "
                         f"pairs. Point area ∝ number of HFF studies. Need index = (country's share of total "
                         f"burden) ÷ (country's share of total spending); expected = total studies × (country "
                         f"need index ÷ sum of all need indices). Dashed line = spending exactly proportional "
                         f"to burden, i.e. every country spending the same amount per DALY.",
             fontsize=8, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.patch.set_facecolor(PAPER)
    ax1.set_facecolor(PAPER)
    ax2.set_facecolor(PAPER)
    # bbox_inches="tight": this footnote is longer than the other two
    # scorecards' (it has to spell out the need-index formula too) and wraps
    # to enough lines to run past the plain canvas edge without it.
    fig.savefig(FIGS / "fig_funder_scorecard_combined.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ---------------------------------------------------------------------------
    # 23-26. Financing-function COMPOSITION (share of a country's classified
    # research) vs. IHME data. Share removes the "bigger countries just have
    # more of everything" confound that made the raw-count correlation matrix
    # uninformative — every pairwise correlation was positive there because it
    # was really measuring overall research volume, not substantive relationships.
    # ---------------------------------------------------------------------------
    country_studies = defaultdict(set)
    for s, c in zip(geo_j["s"], geo_j["c"]):
        country_studies[c].add(s)
    function_studies = defaultdict(set)
    for s, g in zip(function_j["s"], function_j["g"]):
        function_studies[g].add(s)

    comp_funcs = [fn for fn in FUNC_GRPS if fn != "Unclear"]
    comp_palette = dict(zip(comp_funcs, [ACCENT, GOLD, "#1baf7a", "#8a5fb0", "#c0392b",
                                          "#2a9d8f", "#e07b39", "#6b7280", "#3d5a80"]))
    def build_function_share_df(excluded_studies=None):
        """Build country-level financing-function shares after optional study exclusion.

        `excluded_studies` contains study indices to remove BEFORE country-level
        function shares are calculated. This matters for sensitivity analyses:
        excluding the USA should remove every study mapped to the USA from the
        underlying study pool, including USA+other-country multi-country studies,
        rather than merely deleting the USA country observation after aggregation.
        """
        excluded_studies = set() if excluded_studies is None else set(excluded_studies)
        rows = []
        for name, spend in spend_by_country.items():
            i = country_idx[name]
            cs = country_studies.get(i, set()) - excluded_studies
            counts = {
                fn: len(cs & function_studies.get(FUNC_GRPS.index(fn), set()))
                for fn in comp_funcs
            }
            total = sum(counts.values())
            if total < 5:  # too few classified tags for a stable share
                continue
            row = {"country": name, "spend": spend, "total_tags": total}
            for fn in comp_funcs:
                row[fn] = 100 * counts[fn] / total
            rows.append(row)
        return pd.DataFrame(rows)

    comp_df = build_function_share_df()
    log_spend_all = np.log10(comp_df["spend"])

    # --- 23. Small-multiples scatter (facet_wrap style): share vs. spending, one panel per function ---
    ncols = 3
    nrows = -(-len(comp_funcs) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.7 * nrows + 1.6))
    axes = axes.flatten()
    slopes = {}
    for idx, fn in enumerate(comp_funcs):
        ax = axes[idx]
        y = comp_df[fn]
        ax.scatter(comp_df["spend"], y, s=14, color=ACCENT, alpha=0.55, zorder=3, linewidths=0)
        coeffs = np.polyfit(log_spend_all, y, 1)
        xs = np.linspace(log_spend_all.min(), log_spend_all.max(), 50)
        ax.plot(10 ** xs, np.polyval(coeffs, xs), color=GOLD, linewidth=2.25, zorder=4)
        r = float(np.corrcoef(log_spend_all, y)[0, 1])
        slopes[fn] = (coeffs[0], r)
        ax.set_xscale("log")
        title = SHORT_FN.get(fn, fn).replace(": ", ":\n")
        ax.set_title(title, fontsize=8.5, fontweight="bold", color=INK)
        ax.text(0.04, 0.9, f"r={r:.2f}", transform=ax.transAxes, fontsize=8.5, color=SUBHEAD_COLOR, va="top")
        clean_axes(ax)
        ax.tick_params(labelsize=7.5)
    for j in range(len(comp_funcs), len(axes)):
        axes[j].axis("off")
    strongest_fn = max(slopes, key=lambda f: slopes[f][1])
    weakest_fn = min(slopes, key=lambda f: slopes[f][1])
    facet_headline = f"{strongest_fn}'s research share rises fastest with health spending"
    facet_desc = ("Each function's share of a country's classified research vs. health spending per person "
                  "(log x-axis), one panel per function, with a linear trend line.")
    facet_finding = (f"{strongest_fn}'s share rises most with spending (r={slopes[strongest_fn][1]:.2f}); "
                      f"{weakest_fn}'s share falls most (r={slopes[weakest_fn][1]:.2f}).")
    FIG_META["fig_function_share_facets.png"] = (facet_headline, facet_desc, facet_finding)
    fig.subplots_adjust(top=0.78, hspace=0.55, wspace=0.3)
    fig.text(0.02, 0.975, D(facet_headline), fontsize=15, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.925, D(facet_desc), fontsize=10, color=SUBHEAD_COLOR, ha="left", va="top")
    fig.text(0.02, 0.895, D(facet_finding), fontsize=10, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.5, 0.005, "health spending per person, 2023 USD (log)", fontsize=9, color=SUBHEAD_COLOR, ha="center", va="bottom")
    fig.patch.set_facecolor(PAPER)
    for ax in axes:
        ax.set_facecolor(PAPER)
    fig.savefig(FIGS / "fig_function_share_facets.png", dpi=150)
    plt.close(fig)

    # --- 24. Ranked lollipop: correlation of each function's share with spending ---
    def draw_function_share_lollipop(df_in, filename, include_usa=True):
        log_spend_local = np.log10(df_in["spend"])
        local_slopes = {}
        for fn in comp_funcs:
            y = df_in[fn]
            coeffs = np.polyfit(log_spend_local, y, 1)
            r = float(np.corrcoef(log_spend_local, y)[0, 1])
            local_slopes[fn] = (coeffs[0], r)

        lollipop = sorted(local_slopes.items(), key=lambda kv: kv[1][1])
        labels_lol = [SHORT_FN.get(fn, fn) for fn, _ in lollipop]
        r_vals = [v[1] for _, v in lollipop]
        colors_lol = ["#c0392b" if r < 0 else ACCENT for r in r_vals]
        y_pos = np.arange(len(labels_lol))

        fig, ax = plt.subplots(figsize=(8.5, 5.2))
        ax.hlines(y_pos, 0, r_vals, color=colors_lol, linewidth=2, zorder=3)
        ax.scatter(r_vals, y_pos, color=colors_lol, s=90, zorder=4)
        ax.set_yticks(y_pos, labels_lol, fontsize=9.5)
        ax.axvline(0, color="#8a8272", linewidth=0.8, zorder=2)
        for y, r in zip(y_pos, r_vals):
            ax.text(r + (0.03 if r >= 0 else -0.03), y, f"{r:.2f}", va="center",
                    ha="left" if r >= 0 else "right", fontsize=8.5, color=INK)

        top_fn2, bottom_fn2 = lollipop[-1][0], lollipop[0][0]
        desc = "Correlation between each function's share of a country's research and log(health spending per person), across countries."
        base_note = f"Base: {len(df_in)} countries with ≥5 classified financing-function tags matched to IHME health spending per person (F12, 2025)."
        if not include_usa:
            desc += " Studies mapped to the United States of America are excluded before country shares are recalculated."
            base_note = base_note[:-1] + "; all studies mapped to the United States of America excluded before aggregation."

        set_headline(ax, f"{top_fn2}'s research share rises most with health spending",
                     desc,
                     f"{top_fn2} correlates at r={local_slopes[top_fn2][1]:.2f}; {bottom_fn2} correlates at "
                     f"r={local_slopes[bottom_fn2][1]:.2f}" +
                     (", the only clearly negative relationship." if local_slopes[bottom_fn2][1] < -0.1 else "."),
                     filename)
        ax.set_xlabel("correlation with log(health spending per person)")
        ax.set_xlim(-1, 1)
        clean_axes(ax)
        set_footnote(fig, base_note)
        fig.tight_layout()
        fig.savefig(FIGS / filename, dpi=150, bbox_inches="tight")
        plt.close(fig)

    draw_function_share_lollipop(comp_df, "fig_function_share_lollipop.png", include_usa=True)

    # Sensitivity version: remove ALL studies mapped to the USA from the
    # underlying study pool, then recompute country-level financing-function
    # shares and the correlations. This is intentionally different from merely
    # dropping the USA country point after aggregation.
    usa_idx = country_idx.get("United States of America")
    usa_studies = country_studies.get(usa_idx, set()) if usa_idx is not None else set()
    comp_df_no_usa = build_function_share_df(excluded_studies=usa_studies)
    if len(comp_df_no_usa) >= 10:
        draw_function_share_lollipop(
            comp_df_no_usa,
            "fig_function_share_lollipop_no_usa.png",
            include_usa=False,
        )

    # --- 24a-alt. Sensitivity comparison: r-values with all studies vs excluding USA-mapped studies ---
    def calc_function_share_corrs(df_in):
        log_spend_local = np.log10(df_in["spend"])
        corr_map = {}
        for fn in comp_funcs:
            y = df_in[fn]
            corr_map[fn] = float(np.corrcoef(log_spend_local, y)[0, 1])
        return corr_map

    corr_all = calc_function_share_corrs(comp_df)
    corr_no_usa = calc_function_share_corrs(comp_df_no_usa) if len(comp_df_no_usa) >= 10 else None

    # --- 24a-compare. Paired lollipop: all-study vs no-USA r-values in one chart ---
    if corr_no_usa is not None:
        compare_order = sorted(comp_funcs, key=lambda fn: corr_all[fn], reverse=True)
        compare_labels = [SHORT_FN.get(fn, fn) for fn in compare_order]
        compare_labels_wrapped = []
        for lab in compare_labels:
            compare_labels_wrapped.append(
                lab.replace(": ", ":\n")
                   .replace(" other health system inputs", " other health\nsystem inputs")
                   .replace("Public financial management", "Public financial\nmanagement")
                   .replace("Capital investment:\nother health\nsystem inputs", "Capital investment:\nother health system\ninputs")
                   .replace("Recurrent financing (supply chain)", "Recurrent financing\n(supply chain)")
            )
        compare_all_vals = [corr_all[fn] for fn in compare_order]
        compare_no_vals = [corr_no_usa[fn] for fn in compare_order]
        compare_delta = {fn: corr_no_usa[fn] - corr_all[fn] for fn in comp_funcs}
        compare_max_fn = max(comp_funcs, key=lambda fn: abs(compare_delta[fn]))
        y_base = np.arange(len(compare_order))
        y_all = y_base - 0.13
        y_no = y_base + 0.13

        fig, ax = plt.subplots(figsize=(11.2, 6.25))
        ax.axvline(0, color="#8a8272", linewidth=0.9, zorder=1)
        ax.hlines(y_all, 0, compare_all_vals, color="#90b7e1", linewidth=2.2, zorder=2)
        ax.hlines(y_no, 0, compare_no_vals, color="#1f5fa8", linewidth=2.2, zorder=2)
        ax.scatter(compare_all_vals, y_all, s=92, color="#90b7e1", edgecolor="white", linewidth=0.8,
                   zorder=4, label="All studies")
        ax.scatter(compare_no_vals, y_no, s=92, color="#1f5fa8", edgecolor="white", linewidth=0.8,
                   zorder=4, label="Excluding USA-mapped studies")
        ax.set_yticks(y_base, compare_labels_wrapped, fontsize=9.8)
        ax.invert_yaxis()

        # Value labels are vertically offset with their own series, so the two
        # nearly identical r-values remain readable rather than printing on top of each other.
        for y, r in zip(y_all, compare_all_vals):
            ax.text(r + (0.018 if r >= 0 else -0.018), y, f"{r:.2f}",
                    va="center", ha="left" if r >= 0 else "right",
                    fontsize=8.6, color="#557da8")
        for y, r in zip(y_no, compare_no_vals):
            ax.text(r + (0.018 if r >= 0 else -0.018), y, f"{r:.2f}",
                    va="center", ha="left" if r >= 0 else "right",
                    fontsize=8.6, color="#173f73", fontweight="bold")

        set_headline(ax, "Correlation estimates change very little after USA-mapped studies are removed",
                     "Paired lollipops compare each financing function's correlation between country-level research share and log(health spending per person): all studies versus the no-USA sensitivity analysis.",
                     f"The largest shift is for {SHORT_FN.get(compare_max_fn, compare_max_fn)} ({corr_all[compare_max_fn]:.2f} to {corr_no_usa[compare_max_fn]:.2f}).",
                     "fig_function_share_lollipop_all_vs_no_usa.png")
        ax.set_xlabel("correlation with log(health spending per person) (r)")
        x_min = min(compare_all_vals + compare_no_vals)
        x_max = max(compare_all_vals + compare_no_vals)
        ax.set_xlim(min(-0.55, x_min - 0.08), max(0.55, x_max + 0.12))
        clean_axes(ax)
        ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
        ax.tick_params(axis="y", pad=8)
        ax.legend(
            loc="lower right",
            ncol=1,
            frameon=False,
            fontsize=9.2,
            handletextpad=0.8,
            labelspacing=0.75,
            borderaxespad=0.6,
        )
        set_footnote(fig, f"Base: all-studies version uses {len(comp_df):,} countries; no-USA version uses {len(comp_df_no_usa):,} countries. USA-mapped studies are removed before country-level shares are recalculated.")
        fig.subplots_adjust(left=0.33, right=0.96, top=0.76, bottom=0.14)
        fig.savefig(FIGS / "fig_function_share_lollipop_all_vs_no_usa.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    if corr_no_usa is not None:
        corr_order = sorted(comp_funcs, key=lambda fn: corr_all[fn], reverse=True)
        corr_labels = [SHORT_FN.get(fn, fn) for fn in corr_order]
        corr_labels_wrapped = []
        for lab in corr_labels:
            corr_labels_wrapped.append(
                lab.replace(": ", ":\n")
                   .replace(" other health system inputs", " other health\nsystem inputs")
                   .replace("Public financial management", "Public financial\nmanagement")
                   .replace("Capital investment:\nother health\nsystem inputs", "Capital investment:\nother health system\ninputs")
                   .replace("Recurrent financing (supply chain)", "Recurrent financing\n(supply chain)")
            )
        corr_all_vals = [corr_all[fn] for fn in corr_order]
        corr_no_vals = [corr_no_usa[fn] for fn in corr_order]
        corr_delta = {fn: corr_no_usa[fn] - corr_all[fn] for fn in comp_funcs}
        corr_max_fn = max(comp_funcs, key=lambda fn: abs(corr_delta[fn]))
        y_pos = np.arange(len(corr_order))

        fig, ax = plt.subplots(figsize=(11.2, 6.8))
        for y, x1, x2 in zip(y_pos, corr_all_vals, corr_no_vals):
            ax.plot([x1, x2], [y, y], color="#d6dee7", linewidth=2.6, zorder=2)
        ax.scatter(corr_all_vals, y_pos, s=104, color="#90b7e1", edgecolor="white", linewidth=0.9,
                   zorder=3, label="All studies")
        ax.scatter(corr_no_vals, y_pos, s=104, color="#1f5fa8", edgecolor="white", linewidth=0.9,
                   zorder=4, label="Excluding USA-mapped studies")
        ax.set_yticks(y_pos, corr_labels_wrapped, fontsize=9.8)
        ax.invert_yaxis()
        ax.axvline(0, color="#8a8272", linewidth=0.8, zorder=1)
        delta_x = max(corr_all_vals + corr_no_vals) + 0.06
        for y, fn in zip(y_pos, corr_order):
            d = corr_delta[fn]
            ax.text(delta_x, y, f"{d:+.02f}", va="center", ha="left",
                    fontsize=9.0, color=INK, fontweight="bold")
        set_headline(ax, "Removing USA-mapped studies barely changes the correlation pattern",
                     "Each point compares the correlation between a financing function's country-level research share and log(health spending per person) before and after removing all studies mapped to the United States of America.",
                     f"The largest shift is for {SHORT_FN.get(corr_max_fn, corr_max_fn)} ({corr_all[corr_max_fn]:.2f} to {corr_no_usa[corr_max_fn]:.2f}).",
                     "fig_function_share_r_no_usa_dumbbell.png")
        ax.set_xlabel("correlation with log(health spending per person) (r)")
        x_min = min(corr_all_vals + corr_no_vals)
        x_max = max(corr_all_vals + corr_no_vals)
        ax.set_xlim(min(-0.55, x_min - 0.08), max(0.55, x_max + 0.18))
        clean_axes(ax)
        ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
        ax.tick_params(axis="y", pad=8)
        # Keep the two long legend labels on separate rows so they cannot overlap.
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.50, -0.11),
            ncol=1,
            frameon=False,
            fontsize=9.2,
            handletextpad=0.8,
            labelspacing=0.75,
            borderaxespad=0.0,
        )
        set_footnote(fig, f"Base: all-studies version uses {len(comp_df):,} countries; no-USA version uses {len(comp_df_no_usa):,} countries. Numbers at right show the change in r after excluding all USA-mapped studies before aggregation.")
        fig.subplots_adjust(left=0.33, right=0.96, top=0.78, bottom=0.30)
        fig.savefig(FIGS / "fig_function_share_r_no_usa_dumbbell.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    # --- 24b. Sensitivity comparison: overall financing-function mix, all studies vs excluding USA-mapped studies ---
    overall_counts_all = {fn: len(function_studies.get(FUNC_GRPS.index(fn), set())) for fn in comp_funcs}
    overall_counts_no_usa = {fn: len(function_studies.get(FUNC_GRPS.index(fn), set()) - usa_studies) for fn in comp_funcs}
    total_counts_all = sum(overall_counts_all.values())
    total_counts_no_usa = sum(overall_counts_no_usa.values())
    overall_share_all = {fn: 100 * overall_counts_all[fn] / total_counts_all if total_counts_all else 0 for fn in comp_funcs}
    overall_share_no_usa = {fn: 100 * overall_counts_no_usa[fn] / total_counts_no_usa if total_counts_no_usa else 0 for fn in comp_funcs}
    overall_delta_no_usa = {fn: overall_share_no_usa[fn] - overall_share_all[fn] for fn in comp_funcs}

    sens_order = sorted(comp_funcs, key=lambda fn: overall_share_all[fn], reverse=True)
    y_pos = np.arange(len(sens_order))
    sens_labels = [SHORT_FN.get(fn, fn) for fn in sens_order]
    sens_all_vals = [overall_share_all[fn] for fn in sens_order]
    sens_no_vals = [overall_share_no_usa[fn] for fn in sens_order]
    sens_max_fn = max(comp_funcs, key=lambda fn: abs(overall_delta_no_usa[fn]))

    fig, ax = plt.subplots(figsize=(11.2, 6.8))
    wrapped_labels = []
    for lab in sens_labels:
        wrapped_labels.append(
            lab.replace(": ", ":\n")
               .replace(" other health system inputs", " other health\nsystem inputs")
               .replace("Public financial management", "Public financial\nmanagement")
               .replace("Capital investment:\nother health\nsystem inputs", "Capital investment:\nother health system\ninputs")
               .replace("Capital investment:\ninfrastructure", "Capital investment:\ninfrastructure")
               .replace("Recurrent financing (supply chain)", "Recurrent financing\n(supply chain)")
        )
    for y, x1, x2 in zip(y_pos, sens_all_vals, sens_no_vals):
        ax.plot([x1, x2], [y, y], color="#d6dee7", linewidth=2.6, zorder=2)
    ax.scatter(sens_all_vals, y_pos, s=104, color="#90b7e1", edgecolor="white", linewidth=0.9,
               zorder=3, label="All studies")
    ax.scatter(sens_no_vals, y_pos, s=104, color="#1f5fa8", edgecolor="white", linewidth=0.9,
               zorder=4, label="Excluding USA-mapped studies")
    ax.set_yticks(y_pos, wrapped_labels, fontsize=9.8)
    ax.invert_yaxis()
    delta_x = max(sens_all_vals + sens_no_vals) * 1.045
    for y, fn, x2 in zip(y_pos, sens_order, sens_no_vals):
        d = overall_delta_no_usa[fn]
        ax.text(delta_x, y, f"{d:+.1f}pp", va="center", ha="left",
                fontsize=9.0, color=INK, fontweight="bold")
    set_headline(ax, "Removing USA-mapped studies only modestly shifts the global financing-function mix",
                 "Each point compares a financing function's share of all classified function tags in the full dataset versus after removing every study mapped to the United States of America.",
                 f"The largest shift is for {SHORT_FN.get(sens_max_fn, sens_max_fn)} ({overall_delta_no_usa[sens_max_fn]:+.1f} percentage points).",
                 "fig_function_share_no_usa_dumbbell.png")
    ax.set_xlabel("share of classified financing-function tags (%)")
    ax.set_xlim(0, max(sens_all_vals + sens_no_vals) * 1.22)
    clean_axes(ax)
    ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
    ax.tick_params(axis="y", pad=8)
    ax.legend(loc="lower right", frameon=False, fontsize=9.0)
    set_footnote(fig, f"Base: {total_counts_all:,} classified financing-function tags overall; {len(usa_studies):,} studies mapped to the United States of America were removed before recalculating the comparison distribution.")
    fig.subplots_adjust(left=0.33, right=0.96, top=0.78, bottom=0.14)
    fig.savefig(FIGS / "fig_function_share_no_usa_dumbbell.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 24c. Sensitivity comparison ranked by percentage-point change after removing USA-mapped studies ---
    delta_items = sorted(overall_delta_no_usa.items(), key=lambda kv: kv[1])
    delta_labels = [SHORT_FN.get(fn, fn) for fn, _ in delta_items]
    delta_vals = [v for _, v in delta_items]
    delta_colors = ["#c0392b" if v < 0 else ACCENT for v in delta_vals]
    y_pos = np.arange(len(delta_labels))
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    ax.hlines(y_pos, 0, delta_vals, color=delta_colors, linewidth=2.2, zorder=3)
    ax.scatter(delta_vals, y_pos, color=delta_colors, s=90, zorder=4)
    ax.set_yticks(y_pos, delta_labels, fontsize=9.5)
    ax.axvline(0, color="#8a8272", linewidth=0.8, zorder=2)
    for y, v in zip(y_pos, delta_vals):
        ax.text(v + (0.08 if v >= 0 else -0.08), y, f"{v:+.1f}pp", va="center",
                ha="left" if v >= 0 else "right", fontsize=8.6, color=INK)
    set_headline(ax, "Some financing functions become slightly more prominent once USA-mapped studies are removed",
                 "Percentage-point change in each function's share of all classified function tags after removing every study mapped to the United States of America.",
                 f"{SHORT_FN.get(sens_max_fn, sens_max_fn)} changes the most ({overall_delta_no_usa[sens_max_fn]:+.1f} percentage points), showing how small the overall composition shift is.",
                 "fig_function_share_no_usa_delta.png")
    ax.set_xlabel("change in share after removing USA-mapped studies (percentage points)")
    max_abs_delta = max(abs(v) for v in delta_vals) if delta_vals else 1
    ax.set_xlim(-max_abs_delta * 1.35, max_abs_delta * 1.35)
    clean_axes(ax)
    ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
    set_footnote(fig, f"Base: {total_counts_all:,} classified financing-function tags overall; {len(usa_studies):,} USA-mapped studies removed before recalculating shares.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_function_share_no_usa_delta.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 25. Composition bar by spending quartile ---
    comp_df["quartile"] = pd.qcut(comp_df["spend"], 4, labels=["Q1", "Q2", "Q3", "Q4"])
    q_means = comp_df.groupby("quartile", observed=True)[comp_funcs].mean()
    q_means = q_means.div(q_means.sum(axis=1), axis=0) * 100
    delta = q_means.loc["Q4"] - q_means.loc["Q1"]
    biggest_up, biggest_down = delta.idxmax(), delta.idxmin()

    fig, ax = plt.subplots(figsize=(9, 5.4))
    bottom = np.zeros(len(q_means))
    for fn in comp_funcs:
        vals = q_means[fn].values
        ax.bar(q_means.index.astype(str), vals, bottom=bottom, color=comp_palette[fn],
               label=SHORT_FN.get(fn, fn), zorder=3)
        bottom += vals
    set_headline(ax, f"{biggest_up}'s share of research grows the most as countries spend more",
                 "Financing-function mix (% of classified research) by health-spending quartile.",
                 f"{biggest_up}'s share rises {delta[biggest_up]:+.1f}pp from the lowest- to highest-spending "
                 f"quartile, while {biggest_down}'s share falls {delta[biggest_down]:+.1f}pp.",
                 "fig_function_share_quartile.png")
    ax.set_xlabel("health-spending quartile (Q1 lowest, Q4 highest)")
    ax.set_ylabel("share of classified research (%)")
    clean_axes(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False, fontsize=8)
    set_footnote(fig, f"Base: {len(comp_df)} countries split into spending quartiles (IHME F12, 2025); shares "
                       f"are quartile averages, renormalized to 100%.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_function_share_quartile.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- fig_outcome_share_quartile: outcome-domain composition by health-spending quartile ---
    # Same design as fig_function_share_quartile.png (23-26 above), swapping outcome_domain
    # for financing_function.
    outcome_studies = defaultdict(set)
    for s, g in zip(outcome_j["s"], outcome_j["g"]):
        outcome_studies[g].add(s)
    out_comp_outs = [o for o in OUTCOME_GRPS if o != "Unclear"]
    out_comp_palette = dict(zip(out_comp_outs, [ACCENT, GOLD, "#1baf7a", "#8a5fb0", "#c0392b",
                                                 "#2a9d8f", "#e07b39", "#6b7280", "#3d5a80"]))
    out_comp_rows = []
    for name, spend in spend_by_country.items():
        i = country_idx[name]
        cs = country_studies.get(i, set())
        counts = {o: len(cs & outcome_studies.get(OUTCOME_GRPS.index(o), set())) for o in out_comp_outs}
        total = sum(counts.values())
        if total < 5:
            continue
        row = {"country": name, "spend": spend}
        for o in out_comp_outs:
            row[o] = 100 * counts[o] / total
        out_comp_rows.append(row)
    out_comp_df = pd.DataFrame(out_comp_rows)
    out_comp_df["quartile"] = pd.qcut(out_comp_df["spend"], 4, labels=["Q1", "Q2", "Q3", "Q4"])
    out_q_means = out_comp_df.groupby("quartile", observed=True)[out_comp_outs].mean()
    out_q_means = out_q_means.div(out_q_means.sum(axis=1), axis=0) * 100
    out_delta = out_q_means.loc["Q4"] - out_q_means.loc["Q1"]
    out_up, out_down = out_delta.idxmax(), out_delta.idxmin()

    fig, ax = plt.subplots(figsize=(9, 5.4))
    bottom = np.zeros(len(out_q_means))
    for o in out_comp_outs:
        vals = out_q_means[o].values
        ax.bar(out_q_means.index.astype(str), vals, bottom=bottom, color=out_comp_palette[o],
               label=SHORT_OUT.get(o, o), zorder=3)
        bottom += vals
    set_headline(ax, f"{SHORT_OUT.get(out_up, out_up)}'s outcome share grows most as countries spend more",
                 "Outcome-domain mix (% of classified research) by health-spending quartile.",
                 f"{SHORT_OUT.get(out_up, out_up)}'s share rises {out_delta[out_up]:+.1f}pp from the lowest- "
                 f"to highest-spending quartile, while {SHORT_OUT.get(out_down, out_down)}'s share falls "
                 f"{out_delta[out_down]:+.1f}pp.",
                 "fig_outcome_share_quartile.png")
    ax.set_xlabel("health-spending quartile (Q1 lowest, Q4 highest)")
    ax.set_ylabel("share of classified research (%)")
    clean_axes(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False, fontsize=8)
    set_footnote(fig, f"Base: {len(out_comp_df)} countries split into spending quartiles (IHME F12, 2025); "
                       f"shares are quartile averages, renormalized to 100%.")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_outcome_share_quartile.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 26. Bump chart: function rank, DAH boom era vs. bust era (this dataset's own trend) ---
    era_a_years = set(range(2015, 2020))
    era_b_years = set(range(2022, 2026))

    def era_counts(years):
        c = Counter()
        for s, g in zip(function_j["s"], function_j["g"]):
            fn = FUNC_GRPS[g]
            if fn in comp_funcs and year_of_study[s] in years:
                c[fn] += 1
        return c

    avg_a = {fn: era_counts(era_a_years).get(fn, 0) / len(era_a_years) for fn in comp_funcs}
    avg_b = {fn: era_counts(era_b_years).get(fn, 0) / len(era_b_years) for fn in comp_funcs}
    rank_a = {fn: i + 1 for i, fn in enumerate(sorted(comp_funcs, key=lambda f: -avg_a[f]))}
    rank_b = {fn: i + 1 for i, fn in enumerate(sorted(comp_funcs, key=lambda f: -avg_b[f]))}

    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    for fn in comp_funcs:
        ax.plot([0, 1], [rank_a[fn], rank_b[fn]], marker="o", markersize=7, linewidth=2.5,
                color=comp_palette[fn], zorder=3)
        short = SHORT_FN.get(fn, fn)
        ax.text(-0.04, rank_a[fn], f"{short} ({rank_a[fn]})", ha="right", va="center", fontsize=8.5, color=INK)
        ax.text(1.04, rank_b[fn], f"{short} ({rank_b[fn]})", ha="left", va="center", fontsize=8.5, color=INK)
    ax.set_xlim(-1.1, 2.1)
    ax.set_ylim(len(comp_funcs) + 0.6, 0.4)
    ax.set_xticks([0, 1], ["Boom era\n2015–2019 avg/yr", "Bust era\n2022–2025 avg/yr"], fontsize=10)
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    biggest_riser = max(comp_funcs, key=lambda f: rank_a[f] - rank_b[f])
    biggest_faller = min(comp_funcs, key=lambda f: rank_a[f] - rank_b[f])
    bump_desc = ("Rank of each function's average annual study count, DAH boom era (2015–2019) vs. bust "
                 "era (2022–2025).")
    if rank_a[biggest_riser] == rank_b[biggest_riser] and rank_a[biggest_faller] == rank_b[biggest_faller]:
        # No function moved (the v5 case): riser and faller would both be the top
        # function at "rank 1 to 1", so say what actually happened instead.
        top_fn = min(comp_funcs, key=lambda f: rank_a[f])
        set_headline(ax, "Financing-function rankings held steady as global aid crashed", bump_desc,
                     f"No function changed rank between the two eras; {SHORT_FN.get(top_fn, top_fn)} stayed first.",
                     "fig_function_bump_eras.png")
    else:
        set_headline(ax, f"Financing-function rankings shifted as global aid crashed", bump_desc,
                     f"{biggest_riser} climbed from rank {rank_a[biggest_riser]} to {rank_b[biggest_riser]}; "
                     f"{biggest_faller} fell from rank {rank_a[biggest_faller]} to {rank_b[biggest_faller]}.",
                     "fig_function_bump_eras.png")
    set_footnote(fig, "Base: financing-function tags by publication year, this dataset. Eras chosen around the "
                       "2020–2021 COVID-19 DAH spike (IHME).")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_function_bump_eras.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

print("Wrote figures to", FIGS)
for f in sorted(FIGS.glob("*.png")):
    print(" -", f.name, f"({f.stat().st_size / 1024:.0f} KB)")

# ---------------------------------------------------------------------------
# Gallery structure -> content.json. Every fig's title/caption comes straight
# from FIG_META (headline / "desc finding") — one source of truth, matching
# what's baked into the image itself.
# ---------------------------------------------------------------------------
gallery = [
    {
        "title": "Size & growth",
        "blurb": f"How much research is there? {N:,} records in the {SOURCE_NAME} (2010–2026).",
        "figs": [fig_entry("fig_growth.png", "Cumulative growth")],
    },
    {
        "title": "Financing functions & outcomes",
        "blurb": "The core classification: which health-financing function(s) each study addresses, "
                 "and which health-system outcome domain(s) it investigates. A study can carry more "
                 "than one of each, so it is counted in every one it's tagged with.",
        "figs": [
            fig_entry("fig_function_bar.png", "Financing function"),
            fig_entry("fig_function_time.png", "Financing-function mix over time"),
            fig_entry("fig_function_time_lines.png", "Financing-function mix over time (line option)"),
            fig_entry("fig_method_stream.png", "Financing-function output over time"),
            fig_entry("fig_outcome_lollipop.png", "Outcome domain"),
            fig_entry("fig_function_outcome_heatmap.png", "Function vs. outcome"),
        ],
    },
    {
        "title": "Topics & themes",
        "blurb": "What the research is actually about, beyond the financing-function labels: an "
                 "OpenAlex-style field/subfield taxonomy, plus an emergent theme model over the "
                 "abstract text (sentence embeddings → UMAP → HDBSCAN) — the same "
                 "techniques HEE used for its topic-landscape figures.",
        "figs": (
            [fig_entry("fig_topic_landscape.png", "Topic landscape"),
             fig_entry("fig_topic_landscape_treemap.png", "Topic landscape (treemap)"),
             fig_entry("fig_funder_opportunity.png", "The opportunity matrix"),
             fig_entry("fig_disease_method.png", "How each disease area is evaluated"),
             fig_entry("fig_disease_circular.png", "The disease focus of HFF research"),
             fig_entry("fig_transition.png", "LMIC research: communicable to NCD shift"),
             fig_entry("fig_alluvial.png", "Evidence flow: design to function to outcome"),
             fig_entry("fig_map_disease.png", "The disease atlas"),
             fig_entry("fig_funder_trajectory.png", "LMIC research share, era 1 to era 2")] if have_taxonomy else []
        ) + (
            [fig_entry("fig_topicmap.png", "Thematic landscape"),
             fig_entry("fig_theme_rank.png", "Top 20 research themes"),
             fig_entry("fig_topicmap_income.png", "Themes by income skew")] if have_topics else []
        ),
    } if (have_topics or have_taxonomy) else None,
    {
        "title": "Methods & data",
        "blurb": "How the research was done: study design, whether the analysis is quantitative, "
                 "qualitative or mixed, and what kind of data it draws on.",
        "figs": [
            fig_entry("fig_design_bar.png", "Study design"),
            fig_entry("fig_analysis_bar.png", "Type of analysis"),
            fig_entry("fig_datatype_bar.png", "Data type"),
            fig_entry("fig_datasource_bar.png", "Data source"),
        ],
    },
    {
        "title": "Geography",
        "blurb": f"Where the research is about. {n_countries} countries are named in the extracted "
                 f"geography.",
        "figs": [
            fig_entry("fig_top_countries.png", "Top 20 countries"),
            fig_entry("fig_income_bar.png", "Study-country pairs by income group"),
            fig_entry("fig_scope_bar.png", "Geographic scope"),
            fig_entry("fig_burden.png", "Research intensity vs. disease burden"),
            fig_entry("fig_deficit.png", "Studies vs. a burden-proportional share"),
            fig_entry("fig_equity_time.png", "LMIC research share over time"),
            fig_entry("fig_inequality.png", "Evidence concentration among LMICs"),
            fig_entry("fig_injustice.png", "Research relative to disease burden"),
            fig_entry("fig_funder_scorecard.png", "Funding priority scorecard"),
            fig_entry("fig_reach_time.png", "When evidence reached each income group"),
            fig_entry("fig_top_producers.png", "Biggest producers vs. best-served"),
            fig_entry("fig_forest.png", "Adjusted odds ratios by income group"),
        ] + ([
            fig_entry("fig_authorship_pattern.png", "Who leads research about each setting"),
            fig_entry("fig_authorship_by_function.png", "Local authorship, by financing function"),
            fig_entry("fig_authorship_outcome_heatmap.png", "Local authorship, by outcome domain")] if have_authors else []
        ) + ([
            fig_entry("fig_collab_chord.png", "Cross-income co-authorship")] if have_authors else []
        ) + ([
            fig_entry("fig_funder_capacity.png", "Where to build local research capacity")] if have_authors else []
        ) + ([
            fig_entry("fig_funder_funders.png", "The top research funders"),
            fig_entry("fig_funder_funders_treemap.png", "The top research funders (treemap option)"),
            fig_entry("fig_wellcome_priorities.png", "Funding and evidence across Wellcome priority themes"),
            fig_entry("fig_funder_function_heatmap.png", "What each top funder pays for"),
            fig_entry("fig_funder_function_bubbles.png", "What each top funder pays for (bubble option)"),
            fig_entry("fig_funder_outcome_heatmap.png", "What each top funder's research finds"),
            fig_entry("fig_funder_function_mix.png", "Financing-function mix by top funder"),
            fig_entry("fig_funder_trend.png", "Which funders are gaining ground"),
            fig_entry("fig_funder_authorship_alluvial.png",
                      "Funder to financing function to authorship")] if (have_authors and have_funders) else []
        ) + ([
            fig_entry("fig_map_bivariate.png", "Where high burden meets low evidence"),
            fig_entry("fig_map_burden.png", "Research intensity against disease burden (map)"),
            fig_entry("fig_map_deserts.png", "Evidence deserts"),
            fig_entry("fig_map_growth.png", "Where the evidence is youngest"),
            fig_entry("fig_worldmap.png", "Where the evidence is about"),
            fig_entry("fig_map_method.png", "The dominant type of analysis"),
        ] if HAVE_PLOTLY else []) + ([
            fig_entry("fig_map_authorship.png", "Who studies whom")] if (HAVE_PLOTLY and have_authors) else []
        ),
    },
    {
        "title": "Global financing context",
        "blurb": "The real-world backdrop for the Revenue Raising financing function: how much "
                 "development assistance for health (DAH) actually flows, who provides it, and how "
                 "unequally countries fund their own health spending. Source: IHME, Financing Global "
                 "Health 2025: Cuts in Aid and Future Outlook.",
        "figs": (
            [
                fig_entry("fig_dah_trend.png", "Development assistance for health, 1990–2030"),
                fig_entry("fig_dah_cuts_source.png", "The 2025 aid cuts, by source"),
                fig_entry("fig_health_spending_income.png", "Health spending per person, by income group"),
                fig_entry("fig_revenue_vs_dah.png", "Revenue-Raising research vs. real-world aid"),
                fig_entry("fig_functions_vs_dah_index.png", "Every financing function vs. real-world aid"),
                fig_entry("fig_aid_vs_evidence_region.png", "Aid vs. evidence, by region"),
                fig_entry("fig_research_vs_spending_country.png", "Research intensity vs. health spending, by country"),
                fig_entry("fig_funder_scorecard_expenditure.png", "Funding priority scorecard: health expenditure edition"),
                fig_entry("fig_funder_scorecard_combined.png", "Funding priority scorecard: burden, spending and research together"),
                fig_entry("fig_function_share_facets.png", "Each function's research share vs. health spending"),
                fig_entry("fig_function_share_lollipop.png", "Ranked: function share vs. health spending"),
                fig_entry("fig_function_share_lollipop_no_usa.png", "Ranked: function share vs. health spending (excluding USA)"),
                fig_entry("fig_function_share_lollipop_all_vs_no_usa.png", "Paired lollipop: all studies vs excluding USA"),
                fig_entry("fig_function_share_r_no_usa_dumbbell.png", "Correlation sensitivity: all studies vs excluding USA"),
                fig_entry("fig_function_share_no_usa_dumbbell.png", "Global financing-function mix: all studies vs excluding USA"),
                fig_entry("fig_function_share_no_usa_delta.png", "Change in financing-function mix after excluding USA"),
                fig_entry("fig_function_share_quartile.png", "Financing-function mix by spending quartile"),
                fig_entry("fig_outcome_share_quartile.png", "Outcome-domain mix by spending quartile"),
                fig_entry("fig_function_bump_eras.png", "Financing-function ranks, aid boom vs. bust"),
            ] if have_ihme else []
        ),
    } if have_ihme else None,
    {
        "title": "Pipeline",
        "blurb": f"What the {SOURCE_NAME} file contains — from classification to DOI and "
                 "topic-theme recovery. See the Methods tab for the full stage-by-stage "
                 "funnel and what each stage means.",
        "figs": [fig_entry("fig_funnel.png", "Pipeline funnel")],
    },
]

gallery = [sec for sec in gallery if sec is not None]
content["gallery"] = gallery
(DATA / "content.json").write_text(json.dumps(content, allow_nan=False, ensure_ascii=False), encoding="utf-8")
print(f"\nWrote gallery ({sum(len(s['figs']) for s in gallery)} figures across {len(gallery)} sections) into content.json")
