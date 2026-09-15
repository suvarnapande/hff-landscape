"""Generates docs/figures/*.png for the HFF Gallery tab from the already-built
docs/data/*.json (no dependency on the raw 336MB CSV, which isn't committed).

Run: python docs/dex_hff/build_figures.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parent.parent  # docs/
DATA = ROOT / "data"
FIGS = ROOT / "figures"
FIGS.mkdir(exist_ok=True)

ACCENT = "#1f5fa8"
GREY = "#adb5bd"
GOLD = "#b08d3e"
INK = "#10243e"
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


def clean_axes(ax):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#c9c3b3")
    ax.spines["bottom"].set_color("#c9c3b3")
    ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def hbar(counts, title, fname, caption_n=None, color=ACCENT, top=None, xlabel="studies"):
    items = sorted(counts.items(), key=lambda kv: kv[1])
    if top:
        items = items[-top:]
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(8, max(2.2, 0.38 * len(labels) + 0.8)))
    ax.barh(labels, values, color=color, zorder=3)
    for y, v in enumerate(values):
        ax.text(v, y, f"  {v:,}", va="center", fontsize=9, color=INK)
    ax.set_title(title, fontsize=13, color=INK, pad=10, loc="left", fontweight="bold")
    ax.set_xlabel(xlabel)
    clean_axes(ax)
    ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    fig.tight_layout()
    fig.savefig(FIGS / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 1. Growth: studies per year
# ---------------------------------------------------------------------------
year_counts = Counter(studies["year"])
years = sorted(year_counts)
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(years, [year_counts[y] for y in years], color=ACCENT, linewidth=2.5, marker="o", markersize=4)
ax.set_title("Records analysed per year", fontsize=13, loc="left", fontweight="bold", color=INK)
ax.set_ylabel("studies")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=9))
clean_axes(ax)
ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
fig.tight_layout()
fig.savefig(FIGS / "fig_growth.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 2. Financing function counts
# ---------------------------------------------------------------------------
func_counts = Counter()
for g in function_j["g"]:
    func_counts[FUNC_GRPS[g]] += 1
hbar(func_counts, "Studies by financing function\n(a study can carry more than one)",
     "fig_function_bar.png")

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
fig, ax = plt.subplots(figsize=(9, 4.5))
palette = [ACCENT, GOLD, "#1baf7a", "#8a5fb0", GREY]
bottom = [0] * len(years2)
for name, col in zip(top5, palette):
    vals = [100 * by_year_func[y].get(name, 0) / max(totals_by_year[y], 1) for y in years2]
    ax.bar(years2, vals, bottom=bottom, label=name, color=col, zorder=3, width=0.75)
    bottom = [b + v for b, v in zip(bottom, vals)]
ax.set_title("Financing-function mix over time (top 5)\nbars can exceed 100% — a study can carry more than one function",
             fontsize=13, loc="left", fontweight="bold", color=INK)
ax.set_ylabel("share of tagged studies (%)")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=9))
clean_axes(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(FIGS / "fig_function_time.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Outcome domain counts
# ---------------------------------------------------------------------------
outcome_counts = Counter()
for g in outcome_j["g"]:
    outcome_counts[OUTCOME_GRPS[g]] += 1
hbar(outcome_counts, "Studies by outcome domain\n(a study can carry more than one)",
     "fig_outcome_bar.png", color=GOLD)

# ---------------------------------------------------------------------------
# 5-8. Study design / type of analysis / data type / data source
# ---------------------------------------------------------------------------
def col_counts(colname):
    lv = LV[colname]
    c = Counter(studies[colname])
    return {lv[k]: v for k, v in c.items()}


hbar(col_counts("study_design"), "Study design", "fig_design_bar.png")
hbar(col_counts("type_of_analysis"), "Type of analysis", "fig_analysis_bar.png", color=GOLD)
hbar(col_counts("data_type"), "Data type", "fig_datatype_bar.png")
hbar(col_counts("data_source"), "Data source", "fig_datasource_bar.png", color=GOLD)

# ---------------------------------------------------------------------------
# 9. Geographic scope
# ---------------------------------------------------------------------------
hbar(col_counts("geo_scope"), "Geographic scope", "fig_scope_bar.png")

# ---------------------------------------------------------------------------
# 10. Studies by income group
# ---------------------------------------------------------------------------
income_counts = Counter()
seen_sy = set()
for s, c in zip(geo_j["s"], geo_j["c"]):
    inc = countries[c]["income"]
    if inc:
        income_counts[inc] += 1
inc_order = dict_json["meta"]["inc_lv"]
income_counts_ordered = {k: income_counts.get(k, 0) for k in inc_order}
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.bar(list(income_counts_ordered.keys()), list(income_counts_ordered.values()),
       color=[dict_json["meta"]["pal_inc"][i] for i in range(len(inc_order))], zorder=3)
ax.set_title("Study-country pairs by income group", fontsize=13, loc="left", fontweight="bold", color=INK)
ax.set_ylabel("studies")
clean_axes(ax)
ax.grid(axis="y", color="#e7e3da", linewidth=0.8, zorder=0)
plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
fig.tight_layout()
fig.savefig(FIGS / "fig_income_bar.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# 11. Top 20 countries
# ---------------------------------------------------------------------------
country_counts = Counter()
for c in geo_j["c"]:
    country_counts[countries[c]["country"]] += 1
hbar(country_counts, "Top 20 countries by study count", "fig_top_countries.png", top=20)

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
        stages.append(("Input (bucket-screened)", num(row["records"])))
    elif "Passed bucket screen" in lbl:
        stages.append(("Passed bucket screen", num(row["records"])))
    elif "Extraction succeeded" in lbl:
        stages.append(("Extraction succeeded", num(row["records"])))
    elif "DOI recovered" in lbl and "No DOI" not in lbl:
        stages.append(("DOI recovered", num(row["records"])))

mesh_pubmed = next(num(r["records"]) for r in funnel_raw if "PubMed MeSH" in r["label"])
mesh_fallback = next(num(r["records"]) for r in funnel_raw if "OpenAlex fallback" in r["label"])
stages.append(("MeSH/topic theme found", mesh_pubmed + mesh_fallback))

labels = [s[0] for s in stages]
values = [s[1] for s in stages]
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.barh(labels[::-1], values[::-1], color=ACCENT, zorder=3)
for y, v in enumerate(values[::-1]):
    ax.text(v, y, f"  {v:,}", va="center", fontsize=9, color=INK)
ax.set_title("Pipeline funnel", fontsize=13, loc="left", fontweight="bold", color=INK)
ax.set_xlabel("records")
clean_axes(ax)
ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
fig.tight_layout()
fig.savefig(FIGS / "fig_funnel.png", dpi=150, bbox_inches="tight")
plt.close(fig)

print("Wrote figures to", FIGS)
for f in sorted(FIGS.glob("*.png")):
    print(" -", f.name, f"({f.stat().st_size / 1024:.0f} KB)")

# ---------------------------------------------------------------------------
# Gallery structure -> content.json (captions use the counts computed above)
# ---------------------------------------------------------------------------
top_func, top_func_n = func_counts.most_common(1)[0]
top_outcome, top_outcome_n = outcome_counts.most_common(1)[0]
top_design, top_design_n = max(col_counts("study_design").items(), key=lambda kv: kv[1])
top_country, top_country_n = country_counts.most_common(1)[0]
n_countries = len(country_counts)

gallery = [
    {
        "title": "Size & growth",
        "blurb": f"How much research is there? {N:,} records passed the bucket screen and were "
                 f"fully extracted (2010–2026); volume roughly doubled over the period, with "
                 f"2026 partial (data collection ongoing).",
        "figs": [
            {"file": "fig_growth.png", "title": "Records analysed per year",
             "caption": "Growth from 2010 to a 2025 peak; 2026 is a partial year."},
        ],
    },
    {
        "title": "Financing functions & outcomes",
        "blurb": "The core classification: which health-financing function(s) each study addresses, "
                 "and which health-system outcome domain(s) it investigates. A study can carry more "
                 "than one of each, so it is counted in every one it's tagged with.",
        "figs": [
            {"file": "fig_function_bar.png", "title": "Studies by financing function",
             "caption": f"{top_func} is the largest category ({top_func_n:,} studies); "
                        f"capital-investment financing is the smallest."},
            {"file": "fig_function_time.png", "title": "Financing-function mix over time",
             "caption": "The relative mix of the top 5 functions has stayed fairly stable across "
                        "2010–2026; bars exceed 100% because studies overlap functions."},
            {"file": "fig_outcome_bar.png", "title": "Studies by outcome domain",
             "caption": f"{top_outcome} is the most-tagged outcome domain ({top_outcome_n:,} studies)."},
        ],
    },
    {
        "title": "Methods & data",
        "blurb": "How the research was done: study design, whether the analysis is quantitative, "
                 "qualitative or mixed, and what kind of data it draws on.",
        "figs": [
            {"file": "fig_design_bar.png", "title": "Study design",
             "caption": f"{top_design} is the most common design ({top_design_n:,} studies)."},
            {"file": "fig_analysis_bar.png", "title": "Type of analysis",
             "caption": f"{dict_json['meta']['pct_quant']}% of studies are quantitative."},
            {"file": "fig_datatype_bar.png", "title": "Data type",
             "caption": "Cross-sectional data is the most common data type, followed by "
                        "time-series/longitudinal and panel data."},
            {"file": "fig_datasource_bar.png", "title": "Data source",
             "caption": "Administrative data and primary surveys are the two leading data sources."},
        ],
    },
    {
        "title": "Geography",
        "blurb": f"Where the research is about. {n_countries} countries are named in the extracted "
                 f"geography; {dict_json['meta']['pct_single']}% of studies name a single country.",
        "figs": [
            {"file": "fig_top_countries.png", "title": "Top 20 countries by study count",
             "caption": f"{top_country} leads with {top_country_n:,} study-country pairs."},
            {"file": "fig_income_bar.png", "title": "Study-country pairs by income group",
             "caption": "High-income settings carry the largest share of study-country pairs."},
            {"file": "fig_scope_bar.png", "title": "Geographic scope",
             "caption": "Most studies name a single country; a minority are multi-country or "
                        "region/global in scope."},
        ],
    },
    {
        "title": "Pipeline",
        "blurb": "How the dataset itself was built — from the bucket screen through extraction "
                 "to DOI and topic-theme recovery. See the Methods tab for the full stage-by-stage "
                 "funnel and what each stage means.",
        "figs": [
            {"file": "fig_funnel.png", "title": "Pipeline funnel",
             "caption": f"{N:,} records were fully extracted from {dict_json['meta']['n_extracted']:,} "
                        f"bucket-screened input records."},
        ],
    },
]

content["gallery"] = gallery
(DATA / "content.json").write_text(json.dumps(content, allow_nan=False, ensure_ascii=False), encoding="utf-8")
print(f"\nWrote gallery ({sum(len(s['figs']) for s in gallery)} figures across {len(gallery)} sections) into content.json")
