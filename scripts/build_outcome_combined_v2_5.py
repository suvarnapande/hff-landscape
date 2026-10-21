"""[v2.5 copy of build_outcome_combined_v2_4.py: reads the HFF dataset v2.5.1 (v2_5_1/hff_v2_5_1_site.csv); otherwise unchanged.]

One figure for outcome domains with the 'Other' domain unpacked into its themes.

Replaces the side-by-side pair fig_outcome_lollipop.png + fig_outcome_other_themes_v5.png on the
site (both are still built and stay in git; app.js hides them). Rows are outcome domains on one
study-count axis; directly under 'Other', indented lighter rows show its themes, then the studies
that fit no theme. Themes overlap (a study can carry two), so they are not drawn as a stacked bar.

Counting follows the two figures it replaces: outcome_domain_final and outcome_other_theme from the
v2.5.1 site file, a study counts once in every domain/theme it names; 'Not applicable' theme values
are dropped and "Not clustered" + "Other outcome (none of these themes)" form "No theme assigned".

Run after build_figures_v2_5.py and build_fcas_outcomes_v2_5.py (it adds its entry to the
"Financing functions & outcomes" gallery section of content.json, which those regenerate):
    python scripts/build_outcome_combined_v2_5.py
"""
import json
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "docs"  # docs/
DEX = ROOT / "dex_hff"
FIGS = ROOT / "figures"
DATA = ROOT / "data"
SITE_CSV = DEX / "v2_5_1" / "hff_v2_5_1_site.csv"
FNAME = "fig_outcome_combined.png"
SECTION = "Financing functions & outcomes"

INK = "#10243e"
SUBHEAD_COLOR = "#5a6472"
PAPER = "#faf9f6"
GRID = "#edf2f6"
NO_THEME = "#c9cfd6"
# Same ramps as fig_outcome_lollipop (domains) and fig_outcome_other_themes_v5 (themes).
OUT_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "outcome_blue_orange", ["#0b4fb3", "#73a5ea", "#d8e5f4", "#f4c4a4", "#ff8b3d", "#ff5a00"])
SEQ = mcolors.LinearSegmentedColormap.from_list(
    "blue_teal", ["#f1f6f8", "#dcecf3", "#bddbe7", "#8fc7cf", "#5eb2ba", "#2f8f9d", "#1f5fa8"])
THEME_FIX = {"Levels, trends and drivers of spending": "Levels, trends and drivers of spending, prices or funding"}
NO_THEME_VALUES = ("Not clustered", "Other outcome (none of these themes)")

plt.rcParams.update({"font.family": "sans-serif", "font.size": 11, "axes.edgecolor": "#c9c3b3",
                     "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
                     "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER})


def split(v):
    return [t.strip() for t in v.split(";") if t.strip()] if isinstance(v, str) else []


df = pd.read_csv(SITE_CSV, dtype=str, usecols=["outcome_domain_final", "outcome_other_theme"])
N = len(df)
df["outcomes"] = df["outcome_domain_final"].map(lambda v: sorted(set(split(v))))
oc = Counter(o for lst in df["outcomes"] for o in lst)
oth = df[df["outcomes"].map(lambda l: "Other" in l)]
N_OTH = len(oth)
tc = Counter(THEME_FIX.get(t, t) for v in oth["outcome_other_theme"] for t in split(v) if t != "Not applicable")
no_theme = sum(tc.pop(k, 0) for k in NO_THEME_VALUES)

# Rows top to bottom: domains by count, with Other's themes (by count) and "No theme assigned"
# right below the Other row.
domains = [k for k, _ in oc.most_common()]
dom_color = dict(zip(sorted(domains, key=lambda k: oc[k]), [OUT_CMAP(t) for t in np.linspace(0, 1, len(domains))]))
themes = [k for k, _ in tc.most_common()]
norm = mcolors.PowerNorm(gamma=0.6, vmin=min(tc.values()), vmax=max(tc.values()))
rows = []  # (label, value, kind, color)
for d in domains:
    rows.append((d, oc[d], "domain", dom_color[d]))
    if d == "Other":
        rows += [(t, tc[t], "theme", SEQ(0.3 + 0.7 * norm(tc[t]))) for t in themes]
        rows.append(("No theme assigned", no_theme, "theme", NO_THEME))

fig, ax = plt.subplots(figsize=(11.2, 0.36 * len(rows) + 2.6))
fig.subplots_adjust(left=0.36, right=0.95, top=0.84, bottom=0.11)
ypos = np.arange(len(rows))[::-1]
xmax = max(v for _, v, _, _ in rows) * 1.16
pad = xmax * 0.012
for y, (label, v, kind, col) in zip(ypos, rows):
    if kind == "domain":
        ax.hlines(y, 0, v, color=col, linewidth=2.2, zorder=2)
        ax.scatter(v, y, s=130, color=col, edgecolors="white", linewidths=1.2, zorder=3)
        ax.text(v + pad * 1.6, y, f"{v:,}", va="center", fontsize=10.5, fontweight="bold", color=INK)
    else:
        ax.barh(y, v, height=0.62, color=col, zorder=2)
        ax.text(v + pad, y, f"{v:,}", va="center", fontsize=8.8, color=INK)
ax.set_yticks(ypos)
ax.set_yticklabels(["\n".join(textwrap.wrap(l, 44, break_long_words=False)) if k == "domain"
                    else "   " + l for l, _, k, _ in rows])
for tick, (_, _, kind, _) in zip(ax.get_yticklabels(), rows):
    tick.set_fontsize(10.5 if kind == "domain" else 8.8)
    tick.set_color(INK if kind == "domain" else SUBHEAD_COLOR)

# Shade the unpacked block and label it.
theme_y = [y for y, r in zip(ypos, rows) if r[2] == "theme"]
ax.axhspan(min(theme_y) - 0.5, max(theme_y) + 0.5, color="#eef4f6", zorder=0)
ax.text(xmax * 0.985, max(theme_y) + 0.15, f"Themes within the {oc['Other']:,} 'Other' studies\n"
        f"(a study can have two; they overlap)", ha="right", va="top", fontsize=8.6,
        style="italic", color=SUBHEAD_COLOR)

ax.set_xlim(0, xmax)
ax.set_ylim(-0.7, len(rows) - 0.3)
ax.set_xlabel("studies", fontsize=10.5)
ax.tick_params(axis="x", labelsize=9.5)
ax.tick_params(axis="y", length=0)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=6))

second = domains[1]
t1 = themes[0]
headline = "What do the studies measure, and what is inside “Other”?"
desc = ("Studies by outcome domain; a study may examine several. Indented rows break the “Other” domain "
        "into themes.")
finding = (f"“Other” is {oc['Other'] / oc[second]:.1f}× the next domain; its largest theme is "
           f"{t1.lower()} ({tc[t1]:,}).")
fig.text(0.01, 0.975, headline, fontsize=16, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.01, 0.935, desc, fontsize=10.5, color=SUBHEAD_COLOR, ha="left", va="top")
fig.text(0.01, 0.905, finding, fontsize=10.5, fontweight="bold", color=INK, ha="left", va="top")
base = (f"Base: {N:,} studies; {sum(oc.values()):,} outcome-domain tags. Themes: {N_OTH:,} studies tagged “Other”; "
        f"{no_theme:,} ({100 * no_theme / N_OTH:.0f}%) fit no theme. For the September set themes come from clustering the "
        f"“Other” justifications;\nfor studies added in October a language model assigned them.")
fig.text(0.01, 0.025, base, fontsize=8, color=SUBHEAD_COLOR, ha="left", va="top", linespacing=1.4)
fig.savefig(FIGS / FNAME, dpi=150, bbox_inches="tight")
plt.close(fig)

# Gallery entry, placed where fig_outcome_lollipop sits.
entry = {
    "file": FNAME,
    "title": "What do the studies measure?",
    "caption": ("“Other” includes identifiable outcomes outside the eight named groups. The indented rows show "
                "what those “Other” outcomes are. A study may examine several outcomes."),
    "technical_notes": [f"{desc} {finding}", base.replace("\n", " ")],
    "warning": (f"{no_theme:,} studies classified as Other could not be assigned a theme. A study may appear in "
                f"several themes, so the theme rows overlap and do not add up to the Other total."),
}
content = json.loads((DATA / "content.json").read_text(encoding="utf-8"))
section = next(s for s in content["gallery"] if s["title"] == SECTION)
section["figs"] = [f for f in section["figs"] if f["file"] != FNAME]
files = [f["file"] for f in section["figs"]]
at = files.index("fig_outcome_lollipop.png") if "fig_outcome_lollipop.png" in files else len(files)
section["figs"].insert(at, entry)
(DATA / "content.json").write_text(json.dumps(content, allow_nan=False, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {FNAME} ({len(rows)} rows) and its gallery entry")
