"""Financing function x outcome heatmap with the 'Other' outcome unpacked into its themes.

Replaces fig_function_outcome_heatmap.png on the site (still built by build_figures_v2_4.py and
kept in git; app.js hides it). That figure's single 'Other' column held 51-85% of every function's
studies and drowned out the named domains. Here the table is turned on its side so the extra rows
add height, not width: columns are financing functions, rows are the eight named outcome domains
and then the largest 'Other' themes, the remaining themes and 'Other' with no theme.

Counting matches fig_function_outcome_heatmap: function/outcome tags from docs/data/function.json and
outcome.json, 'Unclear' tags dropped, base per function = its studies with at least one outcome tag;
a study counts in every function, domain and theme it carries, so columns can exceed 100%. Themes
come from outcome_other_theme in the v2.4.1 site file, counted only for studies tagged 'Other',
with the same clean-up as fig_outcome_other_themes_v5 / fig_outcome_combined.

Run after build_figures_v2_4.py and build_fcas_outcomes_v2_4.py (it adds its gallery entry to
content.json, which those regenerate):
    python docs/dex_hff/build_function_outcome_themes_v2_4.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # docs/
DEX = ROOT / "dex_hff"
FIGS = ROOT / "figures"
DATA = ROOT / "data"
SITE_CSV = DEX / "v2_4_1" / "hff_v2_4_1_site.csv"
FNAME = "fig_function_outcome_themes.png"
REPLACES = "fig_function_outcome_heatmap.png"
SECTION = "Financing functions & outcomes"
N_THEMES = 11  # all themes; the old 6 + "Remaining" row hid which theme drove large shares

INK = "#10243e"
SUBHEAD_COLOR = "#5a6472"
PAPER = "#faf9f6"
# Same teal ramp as fig_function_outcome_heatmap.
CMAP = mcolors.LinearSegmentedColormap.from_list("fo", ["#deedf0", "#c7e3e6", "#97d1d5", "#4ea8b0", "#0b5964"])
THEME_FIX = {"Levels, trends and drivers of spending": "Levels, trends and drivers of spending, prices or funding"}
NO_THEME_VALUES = ("Not clustered", "Other outcome (none of these themes)")
FN_LABELS = {
    "Benefits decisions": "Benefits\ndecisions",
    "Capital investment: infrastructure": "Capital inv.:\ninfrastructure",
    "Capital investment: other health system inputs": "Capital inv.:\nother inputs",
    "Overall": "Overall",
    "Pooling": "Pooling",
    "Public financial management": "Public financial\nmanagement",
    "Purchasing": "Purchasing",
    "Recurrent financing for the procurement and distribution of supply chain inputs": "Supply chain\nfinancing",
    "Revenue Raising": "Revenue\nraising",
}
OUT_LABELS = {
    "Efficiency in the use of resources": "Efficiency in resource use",
    "Equitable distribution of health system resources": "Equitable distribution of resources",
    "Improved level and distribution of health": "Improved level/distribution of health",
}

plt.rcParams.update({"font.family": "sans-serif", "font.size": 11, "text.color": INK,
                     "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER})


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def split(v):
    return [t.strip() for t in v.split(";") if t.strip()] if isinstance(v, str) else []


dict_json = load("dict.json")
FUNC_GRPS = dict_json["financing_function_grps"]
OUTCOME_GRPS = dict_json["outcome_domain_grps"]
ids = load("studies.json")["id"]
function_j, outcome_j = load("function.json"), load("outcome.json")

s_funcs, s_outs = defaultdict(set), defaultdict(set)
for s, g in zip(function_j["s"], function_j["g"]):
    if FUNC_GRPS[g] != "Unclear":
        s_funcs[s].add(FUNC_GRPS[g])
for s, g in zip(outcome_j["s"], outcome_j["g"]):
    if OUTCOME_GRPS[g] != "Unclear":
        s_outs[s].add(OUTCOME_GRPS[g])

raw = pd.read_csv(SITE_CSV, dtype=str, usecols=["record_id", "outcome_other_theme"])
theme_of_id = dict(zip(raw["record_id"].astype(int), raw["outcome_other_theme"]))
s_themes = {}
for s, outs in s_outs.items():
    if "Other" in outs:
        ts = {THEME_FIX.get(t, t) for t in split(theme_of_id.get(ids[s])) if t != "Not applicable"}
        s_themes[s] = ts - set(NO_THEME_VALUES) or {"No theme"}

theme_n = Counter(t for ts in s_themes.values() for t in ts if t != "No theme")
top_themes = [t for t, _ in theme_n.most_common(N_THEMES)]


def row_keys(s):
    """Rows a study counts in: its named domains, its top themes, 'rest' and/or 'none'."""
    keys = set(s_outs[s]) - {"Other"}
    for t in s_themes.get(s, ()):
        keys.add(t if t in top_themes else ("none" if t == "No theme" else "rest"))
    return keys


funcs = [f for f in FUNC_GRPS if f != "Unclear"]
counts = {f: Counter() for f in funcs}
totals = Counter()
for s, fs in s_funcs.items():
    if not s_outs.get(s):
        continue
    keys = row_keys(s)
    for f in fs:
        totals[f] += 1
        counts[f].update(keys)

overall = Counter()
for s in s_outs:
    overall.update(row_keys(s))
named = sorted([o for o in OUTCOME_GRPS if o not in ("Unclear", "Other")], key=lambda o: -overall[o])
rows = named + top_themes + (["rest"] if len(theme_n) > N_THEMES else []) + ["none"]
row_labels = ([OUT_LABELS.get(o, o) for o in named] + top_themes
              + (["Remaining “Other” themes"] if len(theme_n) > N_THEMES else [])
              + ["“Other”, no theme assigned"])
grid = np.array([[100 * counts[f][r] / totals[f] for f in funcs] for r in rows])

fig, ax = plt.subplots(figsize=(13.4, 12.6))
vmax = max(40, float(grid.max()))
im = ax.imshow(grid, cmap=CMAP, aspect="auto", vmin=0, vmax=vmax)
ax.set_xticks(range(len(funcs)))
ax.set_xticklabels([f"{FN_LABELS.get(f, f)}\n(n={totals[f]:,})" for f in funcs], fontsize=8.9,
                   fontweight="bold", linespacing=1.1)
ax.xaxis.tick_top()
ax.set_yticks(range(len(rows)))
ax.set_yticklabels(row_labels, fontsize=10)
for i, tick in enumerate(ax.get_yticklabels()):
    if i >= len(named):
        tick.set_color(SUBHEAD_COLOR)
ax.tick_params(axis="both", length=0, pad=6)
ax.set_xticks(np.arange(-0.5, len(funcs), 1), minor=True)
ax.set_yticks(np.arange(-0.5, len(rows), 1), minor=True)
ax.grid(which="minor", color="white", linewidth=1.15)
ax.tick_params(which="minor", length=0)
for spine in ax.spines.values():
    spine.set_visible(False)
for i in range(len(rows)):
    for j in range(len(funcs)):
        v = grid[i, j]
        ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=9.6, fontweight="bold",
                color="white" if v >= 0.55 * vmax else INK)

# Divider and label between the named domains and the "Other" theme rows.
split_y = len(named) - 0.5
ax.axhline(split_y, color=INK, linewidth=1.6)
# Block labels to the right of the table.
x_lab = len(funcs) - 0.5 + 0.12
ax.text(x_lab, (len(named) - 1) / 2, "Named outcome domains", rotation=270, ha="left", va="center",
        fontsize=10, fontweight="bold", color=INK, clip_on=False)
ax.text(x_lab, (len(named) + len(rows) - 1) / 2, "“Other” outcomes, by theme", rotation=270,
        ha="left", va="center", fontsize=10, fontweight="bold", color=SUBHEAD_COLOR, clip_on=False)

# Finding: the largest theme share among functions, and the largest named-domain share.
n_th = len(top_themes)  # finding names a real theme, not "remaining"/"no theme"
ti, tj = np.unravel_index(np.argmax(grid[len(named):len(named) + n_th]), (n_th, len(funcs)))
ni, nj = np.unravel_index(np.argmax(grid[:len(named)]), grid[:len(named)].shape)
short_fn = lambda f: FN_LABELS.get(f, f).replace("\n", " ")
headline = "Which outcomes are studied for each financing function?"
desc = ("Share of each function's studies examining each outcome. The “Other” outcome is split into its "
        "main themes; a study can count in several rows.")
finding = (f"Among named outcomes, {short_fn(funcs[nj]).lower()} studies most often examine "
           f"{row_labels[ni].lower()} ({grid[ni, nj]:.0f}%); within “Other”, "
           f"{row_labels[len(named) + ti].lower()} is most common ({short_fn(funcs[tj]).lower()}, "
           f"{grid[len(named) + ti, tj]:.0f}%).")
fig.subplots_adjust(left=0.29, right=0.955, top=0.80, bottom=0.10)
fig.text(0.01, 0.985, headline, fontsize=16, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.01, 0.955, desc, fontsize=10.5, color=SUBHEAD_COLOR, ha="left", va="top")
fig.text(0.01, 0.932, finding, fontsize=10.5, fontweight="bold", color=INK, ha="left", va="top")
cax = fig.add_axes([0.34, 0.05, 0.33, 0.016])
cbar = fig.colorbar(im, cax=cax, orientation="horizontal")
cbar.set_ticks(list(range(0, int(vmax) + 1, 10)))
cbar.set_ticklabels([f"{x}%" for x in range(0, int(vmax) + 1, 10)])
cbar.ax.tick_params(labelsize=8.8, colors=SUBHEAD_COLOR, length=3, pad=2)
cbar.outline.set_visible(False)
fig.text(0.69, 0.058, "Share of the function's studies (%)", ha="left", va="center", fontsize=10, color=INK)
n_base = sum(1 for s in s_outs)
base = (f"Base: {n_base:,} studies with an outcome tag; 'Unclear' tags excluded. Theme rows cover studies tagged "
        f"“Other”; a study can carry two themes.")
fig.text(0.01, 0.012, base, fontsize=8, color=SUBHEAD_COLOR, ha="left", va="bottom")
fig.savefig(FIGS / FNAME, dpi=150, bbox_inches="tight")
plt.close(fig)

entry = {
    "file": FNAME,
    "title": "Which outcomes are studied for each financing function?",
    "caption": ("Each column shows the outcomes examined by studies covering that financing function. The "
                "“Other” outcome is split into its main themes. Darker cells mean a larger share; a study "
                "can count in several rows."),
    "technical_notes": [f"{desc} {finding}", base],
    "warning": "",
}
content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
section = next(s for s in content["gallery"] if s["title"] == SECTION)
section["figs"] = [f for f in section["figs"] if f["file"] != FNAME]
files = [f["file"] for f in section["figs"]]
at = files.index(REPLACES) if REPLACES in files else len(files)
section["figs"].insert(at, entry)
(DATA / "content.json").write_text(json.dumps(content, allow_nan=False, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {FNAME} ({len(rows)} rows x {len(funcs)} functions) and its gallery entry")
