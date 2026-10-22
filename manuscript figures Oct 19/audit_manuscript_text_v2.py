"""v2 of audit_manuscript_text.py (22 October 2026): income groups are the World Bank group of the
country studied in the publication year (audit_common_v2.Data.pub_income), not the current group;
adds the open-access sentence and Figure 7. Expected values are still the manuscript's, so each
DIFF in audit_manuscript_text_report_v2.md is a number the text needs to change.
Run from this folder:  python audit_manuscript_text_v2.py

Audit: every number quoted in the manuscript text (sections 3.2.2, 3.2.3 and the outcomes
paragraph, plus the bases printed on Figures 3 and 4) recomputed from the raw dataset.

Run from this folder:  python audit_manuscript_text.py
Writes audit_manuscript_text_report.md. Statuses: PASS (matches), DIFF (does not match),
INFO (the text has no number to compare; the computed value is shown).

Counting rules, as stated in the text and figure notes:
  - geography: distinct countries matched from geo_final with the site's alias table;
  - 'single-country studies' name exactly one country; income groups are the World Bank group
    of that country in the publication year; WHO regions (Taiwan and Hong Kong, Western Pacific,
    and Kosovo, European, which WHO does not assign, take the WHO region of their UN M49 sub-region);
  - function shares are shares of studies (a study can address several functions);
  - outcome shares use the studies with an outcome domain other than 'Unclear'.
"""
from audit_common_v2 import HERE, OBJECTIVES, Data, pct_matches, report

BD, PUR, POOL, RR, PFM = "Benefits decisions", "Purchasing", "Pooling", "Revenue Raising", "Public financial management"
OVR = "Overall"
SUP = "Recurrent financing for the procurement and distribution of supply chain inputs"
CAP_I, CAP_O = "Capital investment: infrastructure", "Capital investment: other health system inputs"

d = Data()
rows = []


def count(check, expected, actual, note=""):
    rows.append({"check": check, "expected": f"{expected:,}", "actual": f"{actual:,}",
                 "status": "PASS" if expected == actual else "DIFF", "note": note})


def pct(check, expected, actual, note=""):
    if expected is None:
        rows.append({"check": check, "expected": "(missing in text)", "actual": f"{actual:.1f}%",
                     "status": "INFO", "note": note})
        return
    rows.append({"check": check, "expected": f"{expected}%", "actual": f"{actual:.1f}%",
                 "status": "PASS" if pct_matches(actual, expected) else "DIFF", "note": note})


def fn_share(idx, fn):
    return d.share(idx, lambda i: fn in d.functions[i])


ALL = range(d.N)

# ---- 3.2.2 geography --------------------------------------------------------------
named = [i for i in ALL if d.study_countries[i]]
count("3.2.2 studies naming at least one country", 44122, len(named))
pct("3.2.2 share naming at least one country", 83, 100 * len(named) / d.N)
count("3.2.2 study-country pairs", 47488, d.pairs())
count("3.2.2 countries and territories", 198, len(d.countries_named()),
      "site matching: countries in the 185-country reference with at least one study")
single = d.single_country()
pct("3.2.2 single-country studies", 79, 100 * len(single) / d.N)
multi = [i for i in ALL if len(d.study_countries[i]) >= 2 or (not d.no_place[i] and not d.study_countries[i])]
pct("3.2.2 multi-country, regional or global", 14, 100 * len(multi) / d.N)
pct("3.2.2 no place named", 6, 100 * sum(d.no_place) / d.N)
us = [i for i in ALL if "United States of America" in d.study_countries[i]]
count("3.2.2 studies about the United States", 15487, len(us))
pct("3.2.2 share about the United States", 29, 100 * len(us) / d.N)

# ---- 3.2.3 functions, all studies ---------------------------------------------------
for fn, exp in [(BD, 25), (PUR, 22), (POOL, 20), (RR, 16), (PFM, 14), (OVR, 10), (SUP, 9), (CAP_I, 4)]:
    pct(f"3.2.3 all studies: {fn}", exp, fn_share(ALL, fn))
pct("3.2.3 all studies: capital investment (either kind)", 8,
    d.share(ALL, lambda i: bool(d.functions[i] & {CAP_I, CAP_O})))
pct(f"3.2.3 all studies: {CAP_O}", None, fn_share(ALL, CAP_O), "text is cut off after 'other inputs ('")

# ---- 3.2.3 by income group (single-country studies, Figure 3) -------------------------
inc = {i: d.pub_income[(i, c)] for i, c in single.items()}
hic = [i for i, g in inc.items() if g == "High income"]
lmic = [i for i, g in inc.items() if g and g != "High income"]
low = [i for i, g in inc.items() if g == "Low income"]
count("Fig 3 base: single-country studies, high income", 27594, len(hic))
count("Fig 3 base: single-country studies, low and middle income", 14769, len(lmic))
for fn, e_h, e_l in [(PUR, 28, 16), (BD, 28, 21), (RR, 10, 19), (PFM, 13, 19), (OVR, 7, 14), (SUP, 5, 13),
                     (POOL, 22, 23)]:
    pct(f"3.2.3 high income: {fn}", e_h, fn_share(hic, fn))
    pct(f"3.2.3 low and middle income: {fn}", e_l, fn_share(lmic, fn))
for fn, exp in [(RR, 22), (BD, 23), (SUP, 16)]:
    pct(f"3.2.3 low income: {fn}", exp, fn_share(low, fn))

# ---- 3.2.3 by WHO region (single-country studies, Figure 4) ---------------------------
reg = {}
for i, c in single.items():
    reg.setdefault(d.by_name[c]["who_region"], []).append(i)
AFR, AMR, SEAR = "African Region", "Region of the Americas", "South-East Asia Region"
EUR, EMR, WPR = "European Region", "Eastern Mediterranean Region", "Western Pacific Region"
for r, exp in [(AFR, 3730), (AMR, 18743), (EMR, 1658), (EUR, 8704), (SEAR, 2180), (WPR, 7339)]:
    count(f"Fig 4 base: single-country studies, {r}", exp, len(reg[r]))
for r, fn, exp in [(EUR, BD, 28), (WPR, BD, 27), (AMR, BD, 25), (AFR, BD, 22), (EMR, BD, 20), (SEAR, BD, 20),
                   (AMR, POOL, 29), (AMR, PUR, 27), (AFR, RR, 21), (AFR, POOL, 21), (EMR, RR, 21), (EMR, OVR, 20),
                   (SEAR, POOL, 24), (SEAR, PFM, 21), (EUR, PUR, 26), (EUR, PFM, 20), (EUR, POOL, 10)]:
    pct(f"3.2.3 {r}: {fn}", exp, fn_share(reg[r], fn))

# ---- outcomes ------------------------------------------------------------------------
base = d.with_outcome()
count("Outcomes: studies with an outcome domain other than 'Unclear'", 41309, len(base))
pct("Outcomes: share of all studies", 77, 100 * len(base) / d.N)
obj = [i for i in base if d.outcomes[i] & OBJECTIVES]
count("Outcomes: studies examining at least one objective", 20427, len(obj))
pct("Outcomes: share examining at least one objective", 49, 100 * len(obj) / len(base))
only = [i for i in obj if not (d.outcomes[i] - OBJECTIVES - {"Unclear"})]
pct("Outcomes: objectives only", 30, 100 * len(only) / len(base))
pct("Outcomes: objectives and other outcomes", 19, 100 * (len(obj) - len(only)) / len(base))
for o, exp in [("Equitable distribution of health system resources", 15), ("Efficiency in the use of resources", 14),
               ("Improved level and distribution of health", 14), ("Financial protection", 11)]:
    pct(f"Outcomes: {o}", exp, d.share(base, lambda i, o=o: o in d.outcomes[i]))

# ---- open access by income group of the countries studied (publication year) -----------
import re  # noqa: E402

doi = d.raw["doi"].notna() & (d.raw["doi"].astype(str).str.strip() != "")
oa = d.raw["is_oa"].astype(str).eq("True")
oa_grp = {}
for i in range(d.N):
    if not doi[i]:
        continue
    g = {d.pub_income[(i, n)] for n in d.study_countries[i]} - {None}
    oa_grp[i] = ("none" if not g else "hic" if g == {"High income"} else "lmic" if "High income" not in g else "both")
count("OA: studies with a DOI", 42144, len(oa_grp))
pct("OA: share open access", 64, d.share(oa_grp, lambda i: oa[i]))
pct("OA: low and middle income", 73, d.share([i for i, g in oa_grp.items() if g == "lmic"], lambda i: oa[i]))
pct("OA: high income", 59, d.share([i for i, g in oa_grp.items() if g == "hic"], lambda i: oa[i]))

# ---- Figure 7: author location by income group (single-country studies) -----------------
src = (HERE.parent / "scripts" / "build_figures_v2_5.py").read_text(encoding="utf-8")
import ast  # noqa: E402
import pandas as pd  # noqa: E402
ISO2 = ast.literal_eval(re.search(r"ISO2_TO_ISO3 = (\{.*?\n\})", src, re.S).group(1))
auth = pd.read_csv(
    HERE.parent / "docs" / "dex_hff" / "v2_5_1" / "hff_v2_5_1_site.csv", low_memory=False,
    usecols=["author_affiliation_countries"])["author_affiliation_countries"].tolist()
loc = {}
for i, c in single.items():
    v = auth[i]
    ac = {ISO2[t.strip()] for t in re.split(r"[;,]", v) if t.strip() in ISO2} if isinstance(v, str) else set()
    g = inc.get(i)
    if not ac or not g:
        continue
    home = d.by_name[c]["iso3"]
    loc.setdefault(g, []).append("only" if ac == {home} else "mixed" if home in ac else "none")
count("Fig 7 base: single-country studies with an author country", 27982, sum(len(v) for v in loc.values()))
for g, exp in [("Low income", (19, 50, 31)), ("Lower middle income", (35, 43, 21)),
               ("Upper middle income", (55, 34, 10)), ("High income", (80, 17, None))]:
    for k, e in zip(("only", "mixed", "none"), exp):
        pct(f"Fig 7 {g}: authors {k}", e, 100 * loc[g].count(k) / len(loc[g]))

report("Manuscript text audit (publication-year income)", rows, HERE / "audit_manuscript_text_report_v2.md")
