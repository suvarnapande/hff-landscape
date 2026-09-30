"""FCAS and outcome-pattern figures from the HSF extraction 29 Sept v4 file only
(interim, like build_funder_types_v4.py; the rest of the gallery still builds
from the v2 CSV).

v4 fields used:
  fcas                  geo countries on the WB FCAS list in the publication year ('; '-sep)
  income_level          WB income group per geo country (LIC / LMIC / MIC = upper-middle / HIC)
  outcome_domain_final  multi-label outcome domains ('; '-sep)
  outcome_other_theme   non-LLM theme for studies tagged 'Other' ('; '-sep)

Multi-valued fields follow the project convention: a study counts once in every
bucket it names, so shares can sum to >100%.

Outputs (never touches docs/data or docs/figures):
  docs/figures_v4/fig_fcas_countries_v4.png
  docs/figures_v4/fig_fcas_trend_v4.png
  docs/figures_v4/fig_outcome_domains_v4.png
  docs/figures_v4/fig_outcome_other_themes_v4.png
  docs/figures_v4/fig_outcome_trend_v4.png
  docs/figures_v4/fig_outcome_by_context_v4.png
  docs/data_v4/fcas_outcomes_v4.json   headline numbers + figure captions

Run: python docs/dex_hff/build_fcas_outcomes_v4.py
"""
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # docs/
DEX = ROOT / "dex_hff"
FIGS = ROOT / "figures_v4"
DATA = ROOT / "data_v4"
FIGS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
V4 = DEX / "HSF extraction 29 Sept v4.xlsx"
SOURCE = "HSF extraction 29 Sept v4"

# Style constants mirrored from build_figures.py.
ACCENT = "#1f5fa8"
INK = "#10243e"
SUBHEAD_COLOR = "#5a6472"
PAPER = "#faf9f6"
MUTED = "#c9cfd6"
GRID = "#e7e3da"

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

# Same blue-teal ramp build_figures.py uses for count gradients (light -> dark).
SEQ = mcolors.LinearSegmentedColormap.from_list(
    "blue_teal", ["#f1f6f8", "#dcecf3", "#bddbe7", "#8fc7cf", "#5eb2ba", "#2f8f9d", "#1f5fa8"])

SHORT_OUT = {"Equitable distribution of health system resources": "Equitable distribution of resources",
             "Improved level and distribution of health": "Improved level/distribution of health",
             "Efficiency in the use of resources": "Efficiency in resource use"}
COUNTRY_ALIASES = {"Democratic Republic of Congo": "Democratic Republic of the Congo",
                   "DR Congo": "Democratic Republic of the Congo",
                   "Occupied Palestinian Territory": "Palestine",
                   "West Bank and Gaza": "Palestine"}
SHORT_COUNTRY = {"Democratic Republic of the Congo": "DR Congo", "Central African Republic": "CAR"}
INCOME_LABEL = {"LIC": "Low income", "LMIC": "Lower-middle", "MIC": "Upper-middle", "HIC": "High income"}

FIG_META = {}


def split(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return []
    return [t.strip() for t in str(v).split(";") if t.strip()]


def header(fig, headline, desc, finding, fname, top=0.975):
    FIG_META[fname] = {"file": fname, "title": headline, "caption": f"{desc} {finding}"}
    fig.text(0.01, top, headline, fontsize=16, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.01, top - 0.07, desc, fontsize=10.5, color=SUBHEAD_COLOR, ha="left", va="top")
    fig.text(0.01, top - 0.113, finding, fontsize=10.5, fontweight="bold", color=INK, ha="left", va="top")


def footnote(fig, text, y=0.02):
    fig.text(0.01, y, text, fontsize=8, color=SUBHEAD_COLOR, ha="left", va="top", linespacing=1.4)


def clean(ax, grid_axis="x"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def save(fig, fname):
    fig.savefig(FIGS / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)


df = pd.read_excel(V4, sheet_name="Data", dtype=str,
                   usecols=["record_id", "year", "fcas", "income_level", "outcome_domain_final",
                            "outcome_other_theme"])
df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
N = len(df)
df["fcas_list"] = df["fcas"].map(lambda v: sorted({COUNTRY_ALIASES.get(c, c) for c in split(v)}))
df["income_list"] = df["income_level"].map(lambda v: sorted(set(split(v))))
df["outcomes"] = df["outcome_domain_final"].map(lambda v: sorted(set(split(v))))
df["is_fcas"] = df["fcas_list"].map(bool)
# FCAS and income group are both looked up per geo country per publication year,
# so "has a country-level lookup" (income_level set) is the base FCAS is a share of.
df["has_country"] = df["income_list"].map(bool)
N_FCAS = int(df["is_fcas"].sum())
N_COUNTRY = int(df["has_country"].sum())
LAST_WB_YEAR = int(df.loc[df["has_country"], "year"].max())
summary = {"source": SOURCE, "n_studies": N, "n_fcas": N_FCAS, "n_country_level": N_COUNTRY,
           "last_year_with_wb_lookup": LAST_WB_YEAR}

# ---------------------------------------------------------------- FCAS 1: countries
cc = Counter(c for lst in df["fcas_list"] for c in lst)
top = cc.most_common(20)[::-1]
labels = [SHORT_COUNTRY.get(c, c) for c, _ in top]
vals = [n for _, n in top]
fname = "fig_fcas_countries_v4.png"
fig, ax = plt.subplots(figsize=(9.5, 7.6))
fig.subplots_adjust(left=0.2, right=0.95, top=0.83, bottom=0.12)
norm = mcolors.PowerNorm(gamma=0.45, vmin=min(vals), vmax=max(vals))
ax.barh(labels, vals, color=[SEQ(0.3 + 0.7 * norm(v)) for v in vals], height=0.68, zorder=3)
for y, v in enumerate(vals):
    ax.text(v, y, f"  {v:,}", va="center", fontsize=9, color=INK)
ax.set_xlim(0, max(vals) * 1.12)
ax.set_xlabel("studies")
clean(ax)
ng, et = cc["Nigeria"], cc["Ethiopia"]
top2_share = 100 * (ng + et) / N_FCAS
header(fig, "Nigeria and Ethiopia carry the FCAS evidence base",
       "Studies about each fragile or conflict-affected country, top 20.",
       f"{N_FCAS:,} studies ({100 * N_FCAS / N:.1f}% of all) cover an FCAS country; "
       f"Nigeria ({ng}) and Ethiopia ({et}) appear in {top2_share:.0f}% of them.", fname)
footnote(fig, f"Base: {N_FCAS:,} of {N:,} studies whose geo_final names a country on the World Bank FCAS list in the study's "
              f"publication year ({SOURCE}).\nA study covering several FCAS countries counts once per country. "
              f"{len(cc)} FCAS countries appear in total. 'Multiple', 'Global' and region-level studies\ncannot be matched "
              f"and are excluded; studies published after {LAST_WB_YEAR} have no FCAS lookup (World Bank lists end there).",
         y=0.045)
save(fig, fname)
summary["fcas_top_countries"] = dict(cc.most_common(20))

# ---------------------------------------------------------------- FCAS 2: trend
# The fcas column uses each publication year's World Bank list, and big study
# countries joined it mid-period (Nigeria and Burkina Faso 2020, Ethiopia 2022,
# Ukraine 2023), which alone makes the series jump. So a second, fixed-set series
# counts studies on any country that was on the list at some point 2010-LAST_WB_YEAR,
# in every year, to show research growth net of list changes.
EVER_FCAS = {c for lst in df["fcas_list"] for c in lst}
first_listed = {}
for y, lst in zip(df["year"], df["fcas_list"]):
    for c in lst:
        first_listed[c] = min(first_listed.get(c, 9999), int(y))


def geo_countries(v):
    parts = [p.strip() for p in str(v).replace(";", ",").split(",")] if isinstance(v, str) else []
    return {COUNTRY_ALIASES.get(p, p) for p in parts if p}


geo = pd.read_excel(V4, sheet_name="Data", dtype=str, usecols=["geo_final"])["geo_final"]
df["ever_fcas"] = geo.map(lambda v: bool(geo_countries(v) & EVER_FCAS)).values
yrs = df[df["year"].between(2010, LAST_WB_YEAR) & df["has_country"]]
by = yrs.groupby("year").agg(n=("is_fcas", "size"), fcas=("is_fcas", "sum"), fixed=("ever_fcas", "sum"))
by["share"] = 100 * by["fcas"] / by["n"]
by["share_fixed"] = 100 * by["fixed"] / by["n"]
x = by.index.astype(int)
FIXED_COLOR = "#8a96a3"
series = [("fcas", "share", ACCENT, "On that year's FCAS list"),
          ("fixed", "share_fixed", FIXED_COLOR, "Fixed set: ever listed 2010-" + str(LAST_WB_YEAR))]
fname = "fig_fcas_trend_v4.png"
fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7.6), sharex=True, gridspec_kw={"hspace": 0.3})
fig.subplots_adjust(left=0.09, right=0.8, top=0.79, bottom=0.14)
for count_col, share_col, color, label in series:
    for ax, col in ((a1, count_col), (a2, share_col)):
        ax.plot(x, by[col], color=color, linewidth=2, marker="o", markersize=5, zorder=3, label=label)
        end = by[col].iloc[-1]
        ax.text(x[-1] + 0.35, end, f"{end:.0f}" if col == count_col else f"{end:.1f}%", va="center",
                fontsize=9, color=INK, fontweight="bold")
ymax = by[["fcas", "fixed"]].max().max()
marked = [(c, y_) for c, y_ in sorted(first_listed.items(), key=lambda kv: kv[1])
          if c in ("Nigeria", "Ethiopia", "Ukraine") and y_ > 2010]
for i, (c, yr_) in enumerate(marked):
    a1.axvline(yr_, color=GRID, linewidth=1, zorder=1)
    # Stagger heights so labels a year apart don't collide.
    a1.text(yr_, ymax * (1.2 if i % 2 == 0 else 1.08), f"{c} listed", fontsize=8,
            color=SUBHEAD_COLOR, ha="center", va="bottom")
a1.set_ylabel("studies")
a1.set_ylim(0, ymax * 1.36)
clean(a1, "y")
a1.legend(loc="upper left", frameon=False, fontsize=9)
a2.set_ylabel("% of country-level studies")
a2.set_ylim(0, by[["share", "share_fixed"]].max().max() * 1.25)
a2.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
a2.set_xticks(x)
a2.tick_params(axis="x", labelsize=9)
clean(a2, "y")
early = by.loc[2010:2014]
late = by.loc[LAST_WB_YEAR - 4:LAST_WB_YEAR]
early_fixed = 100 * early["fixed"].sum() / early["n"].sum()
late_fixed = 100 * late["fixed"].sum() / late["n"].sum()
late_share = 100 * late["fcas"].sum() / late["n"].sum()
early_share = 100 * early["fcas"].sum() / early["n"].sum()
period = f"{LAST_WB_YEAR - 4}-{str(LAST_WB_YEAR)[2:]}"
header(fig, "FCAS research is growing, but list changes exaggerate the jump",
       "Studies on fragile or conflict-affected countries per year (top) and as a share of country-level studies (bottom).",
       f"By each year's list the share tripled, {early_share:.1f}% (2010-14) to {late_share:.1f}% ({period}); "
       f"on a fixed set of countries it rose only from {early_fixed:.1f}% to {late_fixed:.1f}%.",
       fname)
footnote(fig, f"Base: studies published 2010-{LAST_WB_YEAR} whose geo_final resolves to at least one country with a World Bank "
              f"income/FCAS lookup ({SOURCE}).\nBlue uses the v4 fcas field (the World Bank list in each publication year). "
              f"Grey counts, in every year, studies on any of the {len(EVER_FCAS)} countries listed at some point\n"
              f"2010-{LAST_WB_YEAR}, matched on geo_final. Vertical lines mark the first year the largest study countries count as FCAS. "
              f"{LAST_WB_YEAR + 1} is excluded (no lookup yet).", y=0.06)
save(fig, fname)
summary["fcas_by_year"] = {int(k): {"fcas_that_year": int(r.fcas), "fcas_fixed_set": int(r.fixed),
                                    "country_level": int(r.n), "share_pct": round(r.share, 2),
                                    "share_fixed_pct": round(r.share_fixed, 2)} for k, r in by.iterrows()}
summary["fcas_first_listed_year"] = dict(sorted(first_listed.items(), key=lambda kv: kv[1]))

# ---------------------------------------------------------------- OUTCOME 1: domains
oc = Counter(o for lst in df["outcomes"] for o in lst)
named = [k for k in oc if k not in ("Other", "Unclear")]
order = ["Unclear", "Other"] + sorted(named, key=lambda k: oc[k])
vals = [100 * oc[k] / N for k in order]
fname = "fig_outcome_domains_v4.png"
fig, ax = plt.subplots(figsize=(10, 6.2))
fig.subplots_adjust(left=0.31, right=0.96, top=0.8, bottom=0.13)
cols = [MUTED if k in ("Other", "Unclear") else ACCENT for k in order]
ax.barh([SHORT_OUT.get(k, k) for k in order], vals, color=cols, height=0.66, zorder=3)
for y, (k, v) in enumerate(zip(order, vals)):
    ax.text(v, y, f"  {v:.1f}%  ({oc[k]:,})", va="center", fontsize=9, color=INK)
ax.set_xlim(0, max(vals) * 1.22)
ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax.set_xlabel("share of all studies")
clean(ax)
top_named = max(named, key=lambda k: oc[k])
second = sorted(named, key=lambda k: -oc[k])[1]
n_named_any = int(df["outcomes"].map(lambda l: any(o in named for o in l)).sum())
header(fig, "Most studies measure outcomes outside the named health-system goals",
       "Share of studies investigating each outcome domain (a study can have several).",
       f"'Other' tags {100 * oc['Other'] / N:.0f}% of studies; among named goals, {SHORT_OUT.get(top_named, top_named).lower()} "
       f"({100 * oc[top_named] / N:.0f}%) and {second.lower()} ({100 * oc[second] / N:.0f}%) lead.", fname)
footnote(fig, f"Base: all {N:,} studies ({SOURCE}, outcome_domain_final). {n_named_any:,} studies ({100 * n_named_any / N:.0f}%) "
              f"name at least one of the {len(named)} health-system goals (blue).\nShares sum to >100% because studies are "
              f"multi-label. 'Other' is broken down by theme in the companion figure.", y=0.05)
save(fig, fname)
summary["outcome_domains"] = {k: oc[k] for k in order[::-1]}

# ---------------------------------------------------------------- OUTCOME 2: 'Other' themes
oth = df[df["outcomes"].map(lambda l: "Other" in l)]
N_OTH = len(oth)
tc = Counter(t for v in oth["outcome_other_theme"] for t in split(v) if t not in ("Not applicable",))
not_clustered = tc.pop("Not clustered", 0)
order = sorted(tc, key=lambda k: tc[k])
vals = [100 * tc[k] / N_OTH for k in order]
fname = "fig_outcome_other_themes_v4.png"
fig, ax = plt.subplots(figsize=(10, 6.6))
fig.subplots_adjust(left=0.37, right=0.96, top=0.81, bottom=0.12)
norm = mcolors.PowerNorm(gamma=0.6, vmin=min(vals), vmax=max(vals))
ax.barh(order, vals, color=[SEQ(0.3 + 0.7 * norm(v)) for v in vals], height=0.66, zorder=3)
for y, (k, v) in enumerate(zip(order, vals)):
    ax.text(v, y, f"  {v:.1f}%  ({tc[k]:,})", va="center", fontsize=9, color=INK)
ax.set_xlim(0, max(vals) * 1.25)
ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax.set_xlabel("share of studies tagged 'Other'")
ax.tick_params(axis="y", labelsize=9.5)
clean(ax)
t1, t2 = order[-1], order[-2]
header(fig, "'Other' outcomes are led by access and spending",
       "Themes within the studies whose outcome domain is tagged 'Other'.",
       f"{t1} ({100 * tc[t1] / N_OTH:.0f}%) and {t2.lower()} ({100 * tc[t2] / N_OTH:.0f}%) are the largest themes.", fname)
footnote(fig, f"Base: {N_OTH:,} studies tagged 'Other' in outcome_domain_final ({SOURCE}). Themes come from outcome_other_theme, "
              f"derived without an LLM from a thematic\nanalysis of the 'Other' justifications; a study can carry two themes. "
              f"{not_clustered:,} studies ({100 * not_clustered / N_OTH:.0f}%) fell outside every theme cluster and are not shown.",
         y=0.045)
save(fig, fname)
summary["other_themes"] = dict(tc.most_common()) | {"Not clustered": not_clustered, "n_other": N_OTH}

# ---------------------------------------------------------------- OUTCOME 3: trend, small multiples
named_order = sorted(named, key=lambda k: -oc[k])
yd = df[df["year"].between(2010, 2025)]
tot = yd.groupby("year").size()
fname = "fig_outcome_trend_v4.png"
ncol = 3
nrow = int(np.ceil(len(named_order) / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(11, 2.35 * nrow + 2.2), sharex=True, sharey=True)
fig.subplots_adjust(left=0.07, right=0.97, top=0.79, bottom=0.1, hspace=0.45, wspace=0.12)
yr = tot.index.astype(int)
changes = {}
for i, (ax, k) in enumerate(zip(axes.flat, named_order)):
    s = yd[yd["outcomes"].map(lambda l: k in l)].groupby("year").size().reindex(tot.index, fill_value=0)
    share = 100 * s / tot
    ax.fill_between(yr, share, color=ACCENT, alpha=0.12, linewidth=0)
    ax.plot(yr, share, color=ACCENT, linewidth=2)
    ax.plot(yr[[0, -1]], share.iloc[[0, -1]], "o", color=ACCENT, markersize=5)
    ax.text(yr[0], share.iloc[0], f"{share.iloc[0]:.0f}%  ", ha="right", va="center", fontsize=8.5, color=INK)
    ax.text(yr[-1], share.iloc[-1], f"  {share.iloc[-1]:.0f}%", ha="left", va="center", fontsize=8.5, color=INK,
            fontweight="bold")
    ax.set_title(SHORT_OUT.get(k, k), fontsize=10, loc="left", color=INK, fontweight="bold")
    ax.set_xlim(2008.3, 2026.7)
    ax.set_xticks([2010, 2015, 2020, 2025])
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    clean(ax, "y")
    changes[k] = (share.iloc[0], share.iloc[-1])
for ax in list(axes.flat)[len(named_order):]:
    ax.axis("off")
up1, up2 = sorted(changes, key=lambda k: changes[k][1] - changes[k][0], reverse=True)[:2]
header(fig, "Health outcomes and financial protection gain ground",
       "Share of each year's studies investigating each named health-system goal, 2010-2025.",
       f"{SHORT_OUT.get(up1, up1)} rose from {changes[up1][0]:.0f}% to {changes[up1][1]:.0f}% and "
       f"{SHORT_OUT.get(up2, up2).lower()} from {changes[up2][0]:.0f}% to {changes[up2][1]:.0f}%; the rest barely moved.",
       fname, top=0.985)
footnote(fig, f"Base: {len(yd):,} studies published 2010-2025 ({SOURCE}, outcome_domain_final); 2026 is excluded as a part year. "
              f"Shares are of all studies that year, multi-label.\nPanels share the same y-axis, ordered by overall frequency. "
              f"'Other' and 'Unclear' are not shown.", y=0.045)
save(fig, fname)
summary["outcome_share_2010_vs_2025_pct"] = {k: [round(a, 1), round(b, 1)] for k, (a, b) in changes.items()}

# ---------------------------------------------------------------- OUTCOME x CONTEXT heatmap
groups = [("FCAS", df["is_fcas"])] + [
    (INCOME_LABEL[g], df["income_list"].map(lambda l, g=g: g in l)) for g in ("LIC", "LMIC", "MIC", "HIC")]
rows = named_order
mat = np.array([[100 * df.loc[m, "outcomes"].map(lambda l, k=k: k in l).mean() for _, m in groups] for k in rows])
ns = [int(m.sum()) for _, m in groups]
fname = "fig_outcome_by_context_v4.png"
fig, ax = plt.subplots(figsize=(10, 7.2))
fig.subplots_adjust(left=0.3, right=0.96, top=0.73, bottom=0.14)
ax.imshow(mat, cmap=SEQ, aspect="auto", vmin=0, vmax=mat.max())
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        v = mat[i, j]
        ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=10,
                color="white" if v > 0.55 * mat.max() else INK, fontweight="bold" if j == 0 else "normal")
ax.set_xticks(range(len(groups)))
ax.set_xticklabels([f"{g}\n(n={n:,})" for (g, _), n in zip(groups, ns)], fontsize=9.5)
ax.xaxis.tick_top()
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([SHORT_OUT.get(k, k) for k in rows], fontsize=9.5)
ax.get_xticklabels()[0].set_fontweight("bold")
ax.axvline(0.5, color=PAPER, linewidth=4)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)
fi = rows.index("Financial protection") if "Financial protection" in rows else 0
eff = rows.index("Efficiency in the use of resources") if "Efficiency in the use of resources" in rows else 1
diffs = {k: mat[i, 0] - mat[i, 4] for i, k in enumerate(rows)}
big_up = max(diffs, key=diffs.get)
big_down = min(diffs, key=diffs.get)
header(fig, "FCAS studies look more like low-income than high-income evidence",
       "Share of studies in each setting that investigate each health-system goal.",
       f"Versus high-income settings, FCAS studies focus more on {SHORT_OUT.get(big_up, big_up).lower()} "
       f"({mat[rows.index(big_up), 0]:.0f}% vs {mat[rows.index(big_up), 4]:.0f}%) and less on "
       f"{SHORT_OUT.get(big_down, big_down).lower()} ({mat[rows.index(big_down), 0]:.0f}% vs {mat[rows.index(big_down), 4]:.0f}%).",
       fname)
footnote(fig, f"Base: studies with a World Bank country lookup ({SOURCE}); each column is the share of that group's studies "
              f"tagged with the goal (multi-label).\nFCAS overlaps the income columns (most FCAS countries are low or "
              f"lower-middle income). A study covering countries in several income groups counts in each.\n"
              f"Income group is taken in the publication year; 'Upper-middle' is the v4 'MIC' code.", y=0.06)
save(fig, fname)
summary["outcome_by_context_pct"] = {k: {g: round(mat[i, j], 1) for j, (g, _) in enumerate(groups)}
                                     for i, k in enumerate(rows)}
summary["context_n"] = {g: n for (g, _), n in zip(groups, ns)}

summary["figures"] = list(FIG_META.values())
(DATA / "fcas_outcomes_v4.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
for m in FIG_META.values():
    print(f"{m['file']}\n  {m['title']}\n  {m['caption']}\n")
print(json.dumps({k: summary[k] for k in ("n_fcas", "n_country_level", "last_year_with_wb_lookup", "context_n")}, indent=2))
