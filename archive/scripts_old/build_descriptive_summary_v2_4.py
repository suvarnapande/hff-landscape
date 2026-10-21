"""Four-panel descriptive summary of the included studies, in the site's figure style (layout after
Berrang-Ford et al. 2021, Lancet Planetary Health, Figure 1, without its sampling-frame panel).
Standalone: not added to content.json or shown on the site.

  A  studies per publication year, 2010-2025 (2026 is a partial year and is left out)
  B  studies per financing function ('Unclear' excluded)
  C  studies per World Bank income group of the countries studied (publication-year group)
  D  studies per WHO region of the countries studied

Multi-valued fields follow the site convention: a study counts once in every function, income
group and region it names, so B-D sum to more than the number of studies.

Output: docs/figures/fig_descriptive_summary.png
Run:    python docs/dex_hff/build_descriptive_summary_v2_4.py
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
OUT = ROOT / "figures" / "fig_descriptive_summary.png"

# Site figure style (build_figures_v2_4.py).
INK = "#10243e"
SUBHEAD_COLOR = "#5a6472"
PAPER = "#faf9f6"
GRID = "#e7e3da"
ACCENT = "#1f5fa8"
REGION_COLOR = "#2f8f9d"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


d = load("dict.json")
studies, geo, func = load("studies.json"), load("geo.json"), load("function.json")
countries = {c["country"]: c for c in load("countries.json")}
lv = d["levels"]
N = len(studies["id"])
INC = lv["income"]
INC_COLORS = dict(zip(d["meta"]["inc_lv"], d["meta"]["pal_inc"]))

s_income, s_region = defaultdict(set), defaultdict(set)
for s, c, i in zip(geo["s"], geo["c"], geo["i"]):
    if i is not None and i >= 0:
        s_income[s].add(INC[i])
    reg = countries.get(lv["country"][c], {}).get("who_region")
    if reg:
        s_region[s].add(reg)
s_funcs = defaultdict(set)
for s, g in zip(func["s"], func["g"]):
    name = d["financing_function_grps"][g]
    if name != "Unclear":
        s_funcs[s].add(name)

years = Counter(y for y in studies["year"] if y is not None and 2010 <= y <= 2025)
fn_counts = Counter(f for fs in s_funcs.values() for f in fs)
inc_counts = Counter(g for gs in s_income.values() for g in gs)
reg_counts = Counter(r for rs in s_region.values() for r in rs)

plt.rcParams.update({"font.family": "sans-serif", "font.size": 10, "text.color": INK,
                     "axes.edgecolor": "#c9c3b3", "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "figure.facecolor": PAPER, "axes.facecolor": PAPER,
                     "savefig.facecolor": PAPER})
fig = plt.figure(figsize=(13, 9.4))
# Fixed panel positions: the bottom row leaves room on the left of B and D for their bar labels.
# Panel titles sit at TITLE_X (figure coords) so each lines up with its labels, not its axis.
axA = fig.add_axes([0.07, 0.555, 0.905, 0.265])
axB = fig.add_axes([0.175, 0.095, 0.2, 0.35])
axC = fig.add_axes([0.465, 0.095, 0.17, 0.35])
axD = fig.add_axes([0.80, 0.095, 0.175, 0.35])
TITLE_X = {"A": 0.012, "B": 0.012, "C": 0.405, "D": 0.665}


def clean(ax, grid_axis):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def panel_title(ax, letter, title):
    top = ax.get_position().y1
    fig.text(TITLE_X[letter], top + 0.03, f"{letter}   {title}", fontsize=11.5, fontweight="bold", color=INK,
             ha="left", va="bottom")


def hbars(ax, labels, values, color, xlabel):
    y = range(len(values))[::-1]
    ax.barh(list(y), values, color=color, height=0.66, zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9.4, linespacing=1.05)
    pad = max(values) * 0.02
    for yy, v in zip(y, values):
        ax.text(v + pad, yy, f"{v:,}", va="center", fontsize=8.8, color=INK)
    ax.set_xlim(0, max(values) * 1.22)
    ax.set_xlabel(xlabel, fontsize=9.5)
    ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=4))
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=8.6)
    clean(ax, "x")


# A: studies per year.
yrs = sorted(years)
vals = [years[y] for y in yrs]
axA.fill_between(yrs, vals, color=ACCENT, alpha=0.10, linewidth=0, zorder=2)
axA.plot(yrs, vals, color=ACCENT, linewidth=2.2, zorder=3)
axA.scatter([yrs[0], yrs[-1]], [vals[0], vals[-1]], color=ACCENT, s=28, zorder=4)
for x, v, ha in ((yrs[0], vals[0], "left"), (yrs[-1], vals[-1], "right")):
    axA.annotate(f"{v:,}", (x, v), xytext=(0, 9), textcoords="offset points", ha=ha, fontsize=9.5,
                 fontweight="bold", color=INK)
axA.set_xticks(yrs)
axA.set_xlim(yrs[0] - 0.3, yrs[-1] + 0.3)
axA.set_ylim(0, max(vals) * 1.18)
axA.set_ylabel("studies", fontsize=9.5)
axA.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
axA.tick_params(labelsize=9)
clean(axA, "y")
# Cumulative point without a cumulative line: the year from which half of all studies (2026 included)
# were published, marked on the annual series.
all_years = Counter(y for y in studies["year"] if y is not None)
from_year, n_after = None, 0
for y in sorted(all_years, reverse=True):
    n_after += all_years[y]
    if n_after >= N / 2:
        from_year = y
        break
axA.axvline(from_year, color=SUBHEAD_COLOR, linewidth=1, linestyle=(0, (4, 3)), zorder=2)
axA.fill_between([y for y in yrs if y >= from_year], [years[y] for y in yrs if y >= from_year],
                 color=ACCENT, alpha=0.10, linewidth=0, zorder=2)
axA.text(from_year - 0.12, max(vals) * 0.32,
         f"More than half of all studies ({100 * n_after / N:.0f}%)\nwere published in {from_year} or later",
         ha="right", va="center", fontsize=9.2, color=INK, fontweight="bold")
panel_title(axA, "A", "Studies per publication year")

# B: financing functions, largest first.
FN_SHORT = {"Capital investment: infrastructure": "Capital investment:\ninfrastructure",
            "Capital investment: other health system inputs": "Capital investment:\nother inputs",
            "Public financial management": "Public financial\nmanagement",
            "Recurrent financing for the procurement and distribution of supply chain inputs":
                "Supply chain financing",
            "Revenue Raising": "Revenue raising"}
fns = sorted(fn_counts, key=lambda f: -fn_counts[f])
hbars(axB, [FN_SHORT.get(f, f) for f in fns], [fn_counts[f] for f in fns], ACCENT, "studies")
panel_title(axB, "B", "Financing function")

# C: income groups, low to high, in the site's income colours.
axC.bar(range(len(INC)), [inc_counts[g] for g in INC], color=[INC_COLORS[g] for g in INC], width=0.64,
        zorder=3)
for x, g in enumerate(INC):
    axC.text(x, inc_counts[g] + max(inc_counts.values()) * 0.02, f"{inc_counts[g]:,}", ha="center",
             va="bottom", fontsize=8.8, color=INK)
axC.set_xticks(range(len(INC)))
axC.set_xticklabels(["Low", "Lower\nmiddle", "Upper\nmiddle", "High"], fontsize=9.4)
axC.set_ylim(0, max(inc_counts.values()) * 1.14)
axC.set_ylabel("studies", fontsize=9.5)
axC.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
axC.yaxis.set_major_locator(mticker.MaxNLocator(nbins=4))
axC.tick_params(axis="x", length=0)
axC.tick_params(axis="y", labelsize=8.6)
clean(axC, "y")
panel_title(axC, "C", "Country income group")

# D: WHO regions, largest first.
REG_SHORT = {"Eastern Mediterranean Region": "Eastern Mediterranean", "Region of the Americas": "Americas",
             "South-East Asia Region": "South-East Asia", "Western Pacific Region": "Western Pacific",
             "African Region": "Africa", "European Region": "Europe"}
regs = sorted(d["REGIONS"], key=lambda r: -reg_counts[r])
hbars(axD, [REG_SHORT.get(r, r) for r in regs], [reg_counts[r] for r in regs], REGION_COLOR, "studies")
panel_title(axD, "D", "WHO region")

peak = max(years, key=years.get)
top_reg = REG_SHORT.get(regs[0], regs[0])
fig.text(0.012, 0.98, "Descriptive summary of included studies", fontsize=17, fontweight="bold",
         color=INK, ha="left", va="top")
fig.text(0.012, 0.938, f"{N:,} studies published 2010–2026. A study counts in every financing function, "
         f"income group and region it covers.", fontsize=10.5, color=SUBHEAD_COLOR, ha="left", va="top")
fig.text(0.012, 0.906, f"Annual output grew {vals[-1] / vals[0]:.1f}× from {yrs[0]} to {yrs[-1]}; "
         f"high-income countries and the {top_reg} region account for the most studies.",
         fontsize=10.5, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.012, 0.012, f"Source: HFF dataset v2.4.1. A: 2026 is a partial year and is not shown. "
         f"B: 'Unclear' function tags excluded. C: World Bank income group of each country studied in the "
         f"publication year. D: WHO regions as on the site.", fontsize=8, color=SUBHEAD_COLOR,
         ha="left", va="bottom")
fig.savefig(OUT, dpi=170)
plt.close(fig)

print(f"Wrote {OUT}")
print(f"A: {yrs[0]} {vals[0]:,} -> {yrs[-1]} {vals[-1]:,}; peak {peak}")
print("B:", dict(fn_counts.most_common()))
print("C:", {g: inc_counts[g] for g in INC})
print("D:", {r: reg_counts[r] for r in regs})
