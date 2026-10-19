"""Shared loader for the audit scripts.

Recomputes everything from the raw dataset (docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv), NOT
from the site's processed JSON (docs/data/*.json) or from the CSVs that prep_data.py writes,
so the audits check both pipelines against an independent path.

Reference data that is not a count of studies (country names, population, DALYs, income
group, WHO region) comes from docs/data/countries.json. Country matching uses the site's
alias table, read as text from build_data_v2_5.py (that build is not run).
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
RAW_CSV = DOCS / "dex_hff" / "v2_5_1" / "hff_v2_5_1_site.csv"
BUILD_DATA = DOCS / "dex_hff" / "build_data_v2_5.py"

OBJECTIVES = {"Equitable distribution of health system resources", "Efficiency in the use of resources",
              "Improved level and distribution of health", "Financial protection", "Quality of service provision",
              "Responsiveness to citizens", "Transparency and accountability", "Economic development"}
NOT_NAMED = {"Other", "Unclear", "NA"}
LAST_FULL_YEAR = 2025


def split_multi(v):
    return [t.strip() for t in str(v).split(";") if t.strip()] if pd.notna(v) else []


def _matcher():
    """The site's country matcher (norm + ALIASES + country names), without running the build."""
    src = BUILD_DATA.read_text(encoding="utf-8")
    ns = {"re": re, "unicodedata": unicodedata}
    exec(src[src.index("def norm(s):"):src.index("ALIASES = {norm(k)")], ns)
    a0 = src.index("ALIASES = {")
    a1 = src.index("\n}\n", a0) + 2
    norm = ns["norm"]
    aliases = {norm(k): v for k, v in eval(src[a0 + len("ALIASES = "):a1]).items()}
    return norm, aliases


class Data:
    def __init__(self):
        cols = ["record_id", "year", "doi", "is_oa", "geo_final", "financing_function_final",
                "outcome_domain_final"]
        self.raw = pd.read_csv(RAW_CSV, low_memory=False, usecols=cols)
        self.countries = json.loads((DOCS / "data" / "countries.json").read_text(encoding="utf-8"))
        self.by_name = {c["country"]: c for c in self.countries}
        self.N = len(self.raw)

        norm, aliases = _matcher()
        lookup = {norm(c["country"]): c["country"] for c in self.countries}
        self.study_countries = []   # list of sets of country names, one per study
        self.unmatched = Counter()
        for v in self.raw["geo_final"]:
            names = set()
            if pd.notna(v):
                for tok in {t.strip() for t in str(v).split(",") if t.strip()}:
                    k = norm(tok)
                    name = aliases.get(k) or lookup.get(k)
                    if name:
                        names.add(name)
                    else:
                        self.unmatched[tok] += 1
            self.study_countries.append(names)
        self.no_place = self.raw["geo_final"].isna().tolist()

        self.functions = [set(split_multi(v)) - {"NA"} for v in self.raw["financing_function_final"]]
        self.named_functions = [f - NOT_NAMED for f in self.functions]
        self.outcomes = [set(split_multi(v)) - {"NA"} for v in self.raw["outcome_domain_final"]]
        self.years = self.raw["year"].astype(int).tolist()

    # -- geography ---------------------------------------------------------------
    def pairs(self):
        return sum(len(c) for c in self.study_countries)

    def countries_named(self):
        return {n for c in self.study_countries for n in c}

    def single_country(self):
        """{study index: country name} for studies naming exactly one country."""
        return {i: next(iter(c)) for i, c in enumerate(self.study_countries) if len(c) == 1}

    def region_studies(self):
        out = defaultdict(set)
        for i, cs in enumerate(self.study_countries):
            for n in cs:
                out[self.by_name[n]["who_region"]].add(i)
        return out

    def country_studies(self):
        out = defaultdict(set)
        for i, cs in enumerate(self.study_countries):
            for n in cs:
                out[n].add(i)
        return out

    # -- functions and outcomes --------------------------------------------------
    def share(self, idx, pred):
        idx = list(idx)
        return 100 * sum(1 for i in idx if pred(i)) / len(idx) if idx else float("nan")

    def with_outcome(self):
        return [i for i in range(self.N) if self.outcomes[i] - {"Unclear"}]


def pct_matches(actual, expected):
    """A reported whole-number percentage matches if the actual value rounds to it."""
    return int(actual + 0.5) == expected


def report(title, rows, out_path):
    """rows: dicts with check, expected, actual, status, note. Writes markdown, prints a summary."""
    n = Counter(r["status"] for r in rows)
    lines = [f"# {title}", "", f"PASS {n['PASS']} | DIFF {n['DIFF']} | INFO {n['INFO']}", "",
             "| Status | Check | Expected | Actual | Note |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['status']} | {r['check']} | {r['expected']} | {r['actual']} | {r.get('note', '')} |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{title}: PASS {n['PASS']}, DIFF {n['DIFF']}, INFO {n['INFO']} -> {out_path.name}")
    for r in rows:
        if r["status"] == "DIFF":
            print(f"  DIFF  {r['check']}: expected {r['expected']}, got {r['actual']}  {r.get('note', '')}")
