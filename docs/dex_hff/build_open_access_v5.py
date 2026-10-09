"""Open-access figures from the HSF extraction 29 Sept v5 file, by year and by
the countries the authors are based in.

v5 fields used:
  is_oa                         OpenAlex open-access flag, looked up on the study's DOI. 'False' also
                                means "no DOI / not found", so every share here is of studies WITH a DOI.
  doi
  author_affiliation_countries  ISO 3166-1 alpha-2 codes of author affiliations ('; '-sep, OpenAlex)
Author-country income groups come from docs/data/countries.json (the site's country reference);
countries missing from it (e.g. Taiwan, Israel) have no income group.

Run AFTER build_figures_v5.py (and build_fcas_outcomes_v5.py): it (re)writes the
"Open access & author countries" gallery section in docs/data/content.json.

Outputs:
  docs/figures/fig_map_oa_author_v5.png   world map (same style as the site's other maps; needs plotly + kaleido)
  docs/figures/fig_oa_trend_v5.png
  docs/figures/fig_oa_author_countries_v5.png
  docs/figures/fig_oa_author_income_v5.png
  docs/data/open_access_v5.json   headline numbers + figure captions

Run: python docs/dex_hff/build_open_access_v5.py
"""
import ast
import json
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # docs/
DEX = ROOT / "dex_hff"
FIGS = ROOT / "figures"
DATA = ROOT / "data"
SRC = DEX / "hsf_extraction_29sept_v5.csv"
SOURCE = "HSF extraction 29 Sept v5"
SECTION = "Open access & author countries"

# Style constants mirrored from build_figures.py.
ACCENT = "#1f5fa8"
INK = "#10243e"
SUBHEAD_COLOR = "#5a6472"
PAPER = "#faf9f6"
MUTED = "#c9cfd6"
GRID = "#e7e3da"
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11, "axes.edgecolor": "#c9c3b3", "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": INK, "ytick.color": INK, "figure.facecolor": PAPER,
    "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
})

dict_json = json.loads((DATA / "dict.json").read_text(encoding="utf-8"))
INC_ORDER = dict_json["meta"]["inc_lv"]  # Low -> High, the site's order
INC_COLORS = dict(zip(INC_ORDER, dict_json["meta"]["pal_inc"]))  # same colours as every income chart on the site
countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
INCOME_OF_ISO3 = {c["iso3"]: c["income"] for c in countries}
NAME_OF_ISO3 = {c["iso3"]: c["country"] for c in countries}
SHORT_COUNTRY = {"United States of America": "United States", "United Republic of Tanzania": "Tanzania"}

# Reuse build_figures_v5.py's ISO2 -> ISO3 table rather than keeping a second copy.
_src = (DEX / "build_figures_v5.py").read_text(encoding="utf-8")
ISO2_TO_ISO3 = ast.literal_eval(re.search(r"ISO2_TO_ISO3 = (\{.*?\n\})", _src, re.S).group(1))
ISO3_NAMES_EXTRA = {"TWN": "Taiwan", "ISR": "Israel", "HKG": "Hong Kong", "SGP": "Singapore"}

FIG_META = {}


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


def build_continuous_map_figure(fname, headline, desc, finding, foot, iso3_list, z_list,
                                cmap_stops, vmin, vmax, cbar_ticks, cbar_labels, cbar_title, landcolor="#e5e1d6"):
    """Same layout as build_figures_v5.build_continuous_map_figure (fig_map_authorship etc.):
    Robinson choropleth tile rendered by Plotly+kaleido, composited under the matplotlib
    headline/colorbar/footnote, so this map matches the site's other maps. Copied rather than
    imported because importing build_figures_v5 would run the whole gallery build."""
    import matplotlib.colors as mcolors
    import plotly.graph_objects as go
    FIG_META[fname] = {"file": fname, "title": headline, "caption": f"{desc} {finding}"}
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
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), cax=cbar_ax)
    cb.set_ticks(cbar_ticks)
    cb.set_ticklabels(cbar_labels)
    cb.ax.tick_params(labelsize=8)
    cb.outline.set_visible(False)
    fig.text(0.90, 0.60, cbar_title, fontsize=8, color=SUBHEAD_COLOR, ha="left", va="bottom")
    fig.text(0.02, 0.975, headline, fontsize=15.5, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.02, 0.925, desc, fontsize=9.5, color=SUBHEAD_COLOR, ha="left", va="top", wrap=True)
    fig.text(0.02, 0.875, finding, fontsize=10, fontweight="bold", color=INK, ha="left", va="top", wrap=True)
    fig.text(0.01, 0.02, foot, fontsize=7.6, color=SUBHEAD_COLOR, ha="left", va="bottom", wrap=True)
    fig.patch.set_facecolor(PAPER)
    fig.savefig(FIGS / fname, dpi=150)
    plt.close(fig)
    tmp.unlink(missing_ok=True)


df = pd.read_csv(SRC, dtype=str, usecols=["record_id", "year", "doi", "is_oa", "author_affiliation_countries"])
df["year"] = df["year"].astype(int)
N = len(df)
d = df[df["doi"].notna()].copy()  # OA is only knowable for studies with a DOI
d["oa"] = d["is_oa"].eq("True")
N_DOI = len(d)
OA_ALL = 100 * d["oa"].mean()


def author_iso3(v):
    if not isinstance(v, str) or v.strip() in ("", "Could not find"):
        return []
    return sorted({ISO2_TO_ISO3[t.strip()] for t in re.split(r"[;,]", v) if t.strip() in ISO2_TO_ISO3})


d["auth"] = d["author_affiliation_countries"].map(author_iso3)
a = d[d["auth"].map(bool)].copy()
N_AUTH = len(a)
OA_AUTH = 100 * a["oa"].mean()
summary = {"source": SOURCE, "n_studies": N, "n_with_doi": N_DOI, "oa_share_pct_of_doi": round(OA_ALL, 1),
           "n_with_author_countries": N_AUTH, "oa_share_pct_author_known": round(OA_AUTH, 1)}

# ---------------------------------------------------------------- 1. OA over time
LAST = 2025  # 2026 is a part year
by = d[d["year"].between(2010, LAST)].groupby("year").agg(n=("oa", "size"), oa=("oa", "sum"))
by["share"] = 100 * by["oa"] / by["n"]
x = by.index.astype(int)
fname = "fig_oa_trend_v5.png"
fig, ax = plt.subplots(figsize=(10, 5.8))
fig.subplots_adjust(left=0.08, right=0.93, top=0.77, bottom=0.14)
ax.fill_between(x, by["share"], color=ACCENT, alpha=0.12, linewidth=0)
ax.plot(x, by["share"], color=ACCENT, linewidth=2, marker="o", markersize=5, zorder=3)
for xi in (x[0], x[-1]):
    v = by.loc[xi, "share"]
    ax.annotate(f"{v:.0f}%", (xi, v), xytext=(0, 9), textcoords="offset points", ha="center",
                fontsize=10, fontweight="bold", color=INK)
ax.axhline(50, color=SUBHEAD_COLOR, linewidth=0.8, linestyle=(0, (3, 3)), zorder=2)
ax.text(x[0] - 0.3, 51.2, "half open", fontsize=8.5, color=SUBHEAD_COLOR, ha="left", va="bottom")
ax.set_ylim(0, 100)
ax.set_xlim(x[0] - 0.6, x[-1] + 0.6)
ax.set_xticks(x)
ax.tick_params(axis="x", labelsize=9)
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax.set_ylabel("open-access share of studies with a DOI")
clean(ax, "y")
cross = next((int(y) for y, s in by["share"].items() if s >= 50), None)
header(fig, "Open access has become the norm",
       "Share of each year's studies (with a DOI) that are open access.",
       f"It rose from {by['share'].iloc[0]:.0f}% in {x[0]} to {by['share'].iloc[-1]:.0f}% in {x[-1]}"
       + (f", passing half in {cross}." if cross else "."), fname)
footnote(fig, f"Base: {len(d[d['year'].between(2010, LAST)]):,} studies published 2010-{LAST} with a DOI; "
              f"open-access status from OpenAlex, looked up on the DOI.\n{N - N_DOI:,} studies without a DOI "
              f"are excluded because their status can't be checked. {LAST + 1} is excluded as a part year.", y=0.05)
save(fig, fname)
summary["oa_by_year"] = {int(k): {"n": int(r.n), "oa": int(r.oa), "share_pct": round(r.share, 1)} for k, r in by.iterrows()}

# ---------------------------------------------------------------- 2. OA by author country (top 25)
TOP = 25
MIN_N = 100
cc_n, cc_oa = Counter(), Counter()
for lst, oa in zip(a["auth"], a["oa"]):
    for c in lst:
        cc_n[c] += 1
        cc_oa[c] += int(oa)

# ---------------------------------------------------------------- 2a. OA by author country, world map
MAP_MIN = 20
map_rows = sorted([(c, 100 * cc_oa[c] / cc_n[c], cc_n[c]) for c in cc_n if cc_n[c] >= MAP_MIN], key=lambda r: r[1])
SPAN = 35  # colour range: overall share +/- 35 pts, so cream = the all-studies average
vmin, vmax = max(0, OA_AUTH - SPAN), min(100, OA_AUTH + SPAN)


def cname(c):
    return NAME_OF_ISO3.get(c, ISO3_NAMES_EXTRA.get(c, c))


big = [r for r in map_rows if r[2] >= 200]  # name extremes only among countries with a solid base
lo_c, hi_c = min(big, key=lambda r: r[1]), max(big, key=lambda r: r[1])
n_above = sum(1 for r in map_rows if r[1] > OA_AUTH)
ticks = [t for t in range(0, 101, 10) if vmin <= t <= vmax]
build_continuous_map_figure(
    "fig_map_oa_author_v5.png",
    "Where open-access research comes from",
    "Open-access share of studies with at least one author based in each country. Blue = more open access "
    "than the average study; red = less.",
    f"{n_above} of {len(map_rows)} author countries beat the average study ({OA_AUTH:.0f}%), which the large US output "
    f"({100 * cc_oa['USA'] / cc_n['USA']:.0f}% open) pulls down. Among countries with ≥200 studies, "
    f"{cname(hi_c[0])} is highest ({hi_c[1]:.0f}%) and {cname(lo_c[0])} lowest ({lo_c[1]:.0f}%).",
    f"Base: {N_AUTH:,} studies with a DOI and known author-affiliation countries (open-access status and "
    f"affiliations from OpenAlex), across the {len(map_rows)} author countries with ≥{MAP_MIN} studies (others grey). "
    f"A study counts once for every country its authors are based in.",
    [r[0] for r in map_rows], [r[1] for r in map_rows],
    ["#c0392b", "#f2ead9", "#2a5ea8"], vmin, vmax, ticks, [f"{t}%" for t in ticks], "% open access")
summary["oa_map"] = {"min_studies": MAP_MIN, "n_countries": len(map_rows), "n_above_average": n_above,
                     "colour_midpoint_pct": round(OA_AUTH, 1),
                     "by_country": {cname(c): {"n": n, "oa_share_pct": round(s, 1)} for c, s, n in map_rows[::-1]}}

# ---------------------------------------------------------------- 2b. top-25 bar companion (exact values)
top = [c for c, n in cc_n.most_common(TOP) if n >= MIN_N]
rows = sorted(top, key=lambda c: 100 * cc_oa[c] / cc_n[c])
shares = [100 * cc_oa[c] / cc_n[c] for c in rows]
names = [SHORT_COUNTRY.get(NAME_OF_ISO3.get(c, ISO3_NAMES_EXTRA.get(c, c)), NAME_OF_ISO3.get(c, ISO3_NAMES_EXTRA.get(c, c)))
         for c in rows]
cols = [INC_COLORS.get(INCOME_OF_ISO3.get(c), MUTED) for c in rows]
fname = "fig_oa_author_countries_v5.png"
fig, ax = plt.subplots(figsize=(10, 9.6))
fig.subplots_adjust(left=0.19, right=0.95, top=0.86, bottom=0.16)
ax.barh(names, shares, color=cols, height=0.7, zorder=3)
for yv, (c, s) in enumerate(zip(rows, shares)):
    ax.text(s, yv, f"  {s:.0f}%  (n={cc_n[c]:,})", va="center", fontsize=8.5, color=INK)
ax.axvline(OA_AUTH, color=INK, linewidth=1, linestyle=(0, (3, 3)), zorder=4)
ax.text(OA_AUTH, len(rows) - 0.3, f" all studies {OA_AUTH:.0f}%", fontsize=8.5, color=INK, va="bottom")
ax.set_xlim(0, 100)
ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax.set_xlabel("open-access share of studies with an author based there")
clean(ax)
present = [i for i in INC_ORDER if i in {INCOME_OF_ISO3.get(c) for c in rows}]
handles = [plt.Rectangle((0, 0), 1, 1, color=INC_COLORS[i]) for i in present]
if any(INCOME_OF_ISO3.get(c) is None for c in rows):
    handles.append(plt.Rectangle((0, 0), 1, 1, color=MUTED))
    present = present + ["No income group in site reference"]
# Legend below the axes: inside it, it covers the bottom bars' labels.
ax.legend(handles, present, loc="upper center", bbox_to_anchor=(0.45, -0.07), ncol=len(present), frameon=False,
          fontsize=8.5, title="Author country income", title_fontsize=8.5)
hi, lo = rows[-1], rows[0]
nm = dict(zip(rows, names))
lmic_rows = [c for c in rows if INCOME_OF_ISO3.get(c) in INC_ORDER[:3]]
lmic_mean = np.mean([100 * cc_oa[c] / cc_n[c] for c in lmic_rows]) if lmic_rows else None
hic_rows = [c for c in rows if INCOME_OF_ISO3.get(c) == "High income"]
hic_mean = np.mean([100 * cc_oa[c] / cc_n[c] for c in hic_rows]) if hic_rows else None
header(fig, "Authors in lower-income countries publish open access more often",
       f"Open-access share of studies with at least one author based in each country, the {len(rows)} most active author countries.",
       f"{nm[hi]} tops the list ({100 * cc_oa[hi] / cc_n[hi]:.0f}%) and {nm[lo]} is lowest ({100 * cc_oa[lo] / cc_n[lo]:.0f}%)"
       + (f"; the average is {lmic_mean:.0f}% across middle/low-income author countries vs {hic_mean:.0f}% across high-income ones."
          if lmic_mean is not None and hic_mean is not None else "."), fname, top=0.985)
footnote(fig, f"Base: {N_AUTH:,} studies with a DOI and known author-affiliation countries (OpenAlex). A study counts "
              f"once for every country its authors are based in.\nCountries shown: the {len(rows)} with the most studies "
              f"(each ≥{MIN_N}). Income group is the site's country reference (current World Bank group).", y=0.035)
save(fig, fname)
summary["oa_by_author_country"] = {NAME_OF_ISO3.get(c, ISO3_NAMES_EXTRA.get(c, c)): {"n": cc_n[c], "oa_share_pct": round(100 * cc_oa[c] / cc_n[c], 1)}
                                   for c in rows[::-1]}
summary["income_group_mean_of_top_countries_pct"] = {"L&MICs": None if lmic_mean is None else round(lmic_mean, 1),
                                                    "HIC": None if hic_mean is None else round(hic_mean, 1)}

# ---------------------------------------------------------------- 3. OA by author income group and team make-up
a["incs"] = a["auth"].map(lambda l: {INCOME_OF_ISO3.get(c) for c in l})
known = a[a["incs"].map(lambda s: None not in s)].copy()  # every author country has an income group
N_KNOWN = len(known)
inc_n = {g: int(known["incs"].map(lambda s, g=g: g in s).sum()) for g in INC_ORDER}
inc_share = {g: 100 * known.loc[known["incs"].map(lambda s, g=g: g in s), "oa"].mean() for g in INC_ORDER}


def team(s):
    has_h = "High income" in s
    has_l = bool(s - {"High income"})
    return "High-income authors only" if has_h and not has_l else ("Mixed high-income and L&MICs team" if has_h else "L&MICs authors only")


known["team"] = known["incs"].map(team)
TEAM_ORDER = ["High-income authors only", "Mixed high-income and L&MICs team", "L&MICs authors only"]
team_n = known["team"].value_counts().reindex(TEAM_ORDER).fillna(0).astype(int)
team_share = known.groupby("team")["oa"].mean().reindex(TEAM_ORDER) * 100

fname = "fig_oa_author_income_v5.png"
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5.6), gridspec_kw={"wspace": 0.95})
fig.subplots_adjust(left=0.14, right=0.93, top=0.72, bottom=0.17)
inc_rows = INC_ORDER[::-1]  # High at top
a1.barh(inc_rows, [inc_share[g] for g in inc_rows], color=[INC_COLORS[g] for g in inc_rows], height=0.62, zorder=3)
for yv, g in enumerate(inc_rows):
    a1.text(inc_share[g], yv, f"  {inc_share[g]:.0f}%  (n={inc_n[g]:,})", va="center", fontsize=9, color=INK)
a1.set_title("Any author from this income group", loc="left", fontsize=10.5, fontweight="bold", color=INK)
t_rows = TEAM_ORDER[::-1]
a2.barh(t_rows, [team_share[t] for t in t_rows], color=ACCENT, height=0.55, zorder=3)
for yv, t in enumerate(t_rows):
    a2.text(team_share[t], yv, f"  {team_share[t]:.0f}%  (n={team_n[t]:,})", va="center", fontsize=9, color=INK)
a2.set_title("Author-team make-up", loc="left", fontsize=10.5, fontweight="bold", color=INK)
for ax in (a1, a2):
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_xlabel("open-access share")
    ax.axvline(OA_AUTH, color=INK, linewidth=1, linestyle=(0, (3, 3)), zorder=4)
    clean(ax)
a2.tick_params(axis="y", labelsize=9.5)
ho, mx, lo_ = (team_share[t] for t in TEAM_ORDER)
header(fig, "Research with lower-income authors is more often open access",
       "Open-access share by where a study's authors are based (dashed line: all studies).",
       f"{lo_:.0f}% of L&MICs-only author teams publish open access and {mx:.0f}% of mixed teams, vs {ho:.0f}% "
       f"of teams based only in high-income countries.", fname)
footnote(fig, f"Base: {N_KNOWN:,} studies with a DOI whose author countries all have an income group in the site's country "
              f"reference (OpenAlex).\nLeft: a study counts in every income group its authors come from. "
              f"L&MICs = low- and middle-income. {N_AUTH - N_KNOWN:,} studies with an author in a country missing from the "
              f"reference\n(e.g. Taiwan, Israel) are left out.", y=0.07)
save(fig, fname)
summary["oa_by_author_income_pct"] = {g: {"n": inc_n[g], "oa_share_pct": round(inc_share[g], 1)} for g in INC_ORDER}
summary["oa_by_team_pct"] = {t: {"n": int(team_n[t]), "oa_share_pct": round(team_share[t], 1)} for t in TEAM_ORDER}
summary["n_income_known"] = N_KNOWN

summary["figures"] = list(FIG_META.values())
(DATA / "open_access_v5.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------------------------------------------------------------- gallery section
cpath = DATA / "content.json"
content = json.loads(cpath.read_text(encoding="utf-8"))
gallery = [s for s in content["gallery"] if s["title"] != SECTION]
section = {
    "title": SECTION,
    "blurb": (f"How much of the evidence is free to read, and where the authors behind it are based. Open-access status "
              f"comes from OpenAlex via each study's DOI, so it covers the {N_DOI:,} studies ({100 * N_DOI / N:.0f}%) that "
              f"have one; author countries are the affiliation countries OpenAlex records."),
    "figs": [FIG_META[f] for f in ("fig_map_oa_author_v5.png", "fig_oa_trend_v5.png", "fig_oa_author_income_v5.png",
                                   "fig_oa_author_countries_v5.png")],
}
pos = next((i for i, s in enumerate(gallery) if s["title"] == "Pipeline"), len(gallery))
gallery.insert(pos, section)
content["gallery"] = gallery
cpath.write_text(json.dumps(content, allow_nan=False, ensure_ascii=False), encoding="utf-8")
print(f"gallery section '{SECTION}' written")
for m in FIG_META.values():
    print(f"\n{m['file']}\n  {m['title']}\n  {m['caption']}")
print(json.dumps({k: summary[k] for k in ("n_with_doi", "oa_share_pct_of_doi", "n_with_author_countries", "n_income_known",
                                          "oa_by_team_pct", "income_group_mean_of_top_countries_pct")}, indent=1))
