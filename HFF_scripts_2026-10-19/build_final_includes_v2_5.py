#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Build HFF v2.5 = v2.4 + Decision 17 (HTAs are Benefits decisions) + the HEE overlap flag.

    python -X utf8 projects/hff/final_includes/build_final_includes_v2_5.py [--replace-v2-5]

Run from the REPO ROOT. Local only. Reads v2.4, never writes it; refuses to overwrite its own
outputs unless --replace-v2-5.

DECISION 17 (B. Hutchinson 2026-10-06; scope and overlap answered 2026-10-13): any record that
describes itself as an HTA is Benefits decisions in the HFF arm. v2.4's labels came from codebook
v52 (2026-10-07/09), which sent HTAs to HEE unless they stated a coverage decision.
  Inputs (all git-ignored, record level, under final_includes/hta_v2_5/):
    hta_check.jsonl   hta_check_v2_5.py: 504 candidates (an HTA term in title/abstract AND either
                      excluded as no_financing_function_at_relabel or included without Benefits
                      decisions), each judged by deepseek-v4.1-flash "does the record present itself
                      as an HTA"; a yes counts only with a verified quote.
    extract/          hta_extract_v2_5.py: the non-financing fields for re-included records never
                      extracted (run_hff_extract_new_v52, unchanged).
    metadata.jsonl    hta_metadata_v2_5.py: bibliographic metadata for re-included October-origin
                      records (enrich_metadata_v2_2.one, unchanged).
  Applied:
    * excluded HTA records (no_financing_function_at_relabel) -> included, function
      "Benefits decisions", function_label_source = "hta_rule_decision17"; a re-included record that
      duplicates an included study (DOI, or normalised title + year) stays out as duplicate_doi /
      duplicate (none on 2026-10-13, asserted by the count printed);
    * included HTA records without Benefits decisions -> "Benefits decisions" added FIRST (it becomes
      primary_function), other functions kept after it; function_label_source unchanged.
    The pre-ruling label is kept in financing_function_v52_pre_hta; hta_decision17 = True marks
    every record the rule changed. Re-included records are not in the topic model (fitted on the
    v2.3 included set): their topic columns are null.
HEE OVERLAP (Decision 17, point 2): also_in_hee = the study is also included in HEE v2 (41,657,
is_eligible in projects/hee/analysis/data/hee_analysis_master.csv). Report arms separately; never
sum the counts.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FI = ROOT / "projects/hff/final_includes"
sys.path.insert(0, str(FI))
import build_final_includes_v2_2 as B  # noqa: E402  (extraction, geo and World Bank helpers)
from hta_extract_v2_5 import hta_yes  # noqa: E402

IN_INC, IN_ADS = FI / "hff_includes_final_v2_4.parquet", FI / "hff_analysis_dataset_v2_4.parquet"
IN_PRISMA = FI / "PRISMA_v2_4.json"
EXTRACT = FI / "hta_v2_5/extract/raw_extract.jsonl"
META = FI / "hta_v2_5/metadata.jsonl"
HEE = ROOT / "projects/hee/analysis/data/hee_analysis_master.csv"
OUT_INC, OUT_ADS = FI / "hff_includes_final_v2_5.parquet", FI / "hff_analysis_dataset_v2_5.parquet"
OUT_META, OUT_PRISMA = FI / "hff_includes_final_v2_5_meta.json", FI / "PRISMA_v2_5.json"
BEN = "Benefits decisions"
META_COLS = ["doi", "doi_confidence", "language", "ml_topics", "ml_thematic_cluster", "mesh_theme",
             "mesh_source", "authors", "author_affiliation_institutions", "author_affiliation_countries",
             "author_keywords", "keywords_openalex_generated", "journal", "volume", "issue", "pages",
             "biblio_source", "url", "publisher_location", "research_funder", "pathways",
             "language_source", "is_oa", "oa_url"]


def relabel(df: pd.DataFrame, ids: set[str]) -> pd.DataFrame:
    m = df["record_id"].isin(ids)
    df["financing_function_v52_pre_hta"] = df["financing_function_v52"]
    df["hta_decision17"] = m
    new = [[BEN] + [f for f in B.split_functions(v) if f != BEN] for v in df.loc[m, "financing_function_v52"]]
    df.loc[m, "financing_function_v52"] = [";".join(x) for x in new]
    df.loc[m, "func_list"] = pd.Series([np.array(x, dtype=object) for x in new], index=df.index[m])
    df.loc[m, "primary_function"] = BEN
    df.loc[m, "n_functions"] = [len(x) for x in new]
    df.loc[m, "labelled"] = True
    return df


def main() -> None:
    if "--replace-v2-5" not in sys.argv:
        for p in (OUT_INC, OUT_ADS, OUT_META, OUT_PRISMA):
            if p.exists():
                raise SystemExit(f"{p.name} exists; refusing to overwrite (pass --replace-v2-5)")
    inc, ads = pd.read_parquet(IN_INC), pd.read_parquet(IN_ADS)
    for f in (inc, ads):
        f["record_id"] = f["record_id"].astype(str)
    assert (inc["record_id"].values == ads["record_id"].values).all()
    yes = hta_yes()
    back = set(ads.loc[ads["record_id"].isin(yes) & (ads["exclusion_reason_v2"] == "no_financing_function_at_relabel"), "record_id"])
    add = set(ads.loc[ads["record_id"].isin(yes) & ads["analysis_include"], "record_id"])

    # duplicates of the re-included against the included set (v2.4 rules: DOI, else title + year)
    ai = ads[ads["analysis_include"]]
    dois = set(ai["doi"].map(B.norm_doi)) - {""}
    ty = set(ai["title"].map(B.norm_title) + "|" + ai["year"].astype(str))
    r = ads[ads["record_id"].isin(back)]
    dup_doi = set(r.loc[r["doi"].map(B.norm_doi).isin(dois), "record_id"])
    dup_ty = set(r.loc[(r["title"].map(B.norm_title) + "|" + r["year"].astype(str)).isin(ty), "record_id"]) - dup_doi
    back_ok = back - dup_doi - dup_ty

    # extraction + geo + income for re-included rows never extracted
    x = B.load_extraction(EXTRACT)
    x = x[x["record_id"].isin(back_ok)].set_index("record_id")
    wb, wb_date = B.load_wb()
    meta = {}
    if META.exists():
        for ln in META.open(encoding="utf-8"):
            if ln.strip():
                d = json.loads(ln)
                meta[d["record_id"]] = d

    def apply(df: pd.DataFrame, analysis: bool) -> pd.DataFrame:
        df = df.copy()
        df = relabel(df, add | back_ok)
        mb = df["record_id"].isin(back_ok)
        df.loc[mb, "analysis_include"] = True
        df.loc[mb, "exclusion_reason_v2"] = None
        df.loc[mb, "function_label_source"] = "hta_rule_decision17"
        df.loc[df["record_id"].isin(dup_doi), "exclusion_reason_v2"] = "duplicate_doi"
        df.loc[df["record_id"].isin(dup_ty), "exclusion_reason_v2"] = "duplicate"
        if analysis:
            for rid in x.index:
                i = df.index[df["record_id"] == rid][0]
                for c in x.columns:
                    if c in df.columns:
                        df.at[i, c] = x.at[rid, c]
                for c in B.SPLIT:
                    df.at[i, c] = 0.0
                g = B.GEO.enrich_geo(df.at[i, "geo_final"] or "", int(df.at[i, "year"]) if pd.notna(df.at[i, "year"]) else None)
                df.at[i, "continent"], df.at[i, "fcas"], df.at[i, "geo_derivation_note"] = g["continent"] or None, g["fcas"] or None, g["geo_derivation_note"] or None
                df.at[i, "income_level_bundled"] = g["income_level"] or None
                inc_wb, unres = B.wb_income(df.at[i, "geo_final"], wb)
                df.at[i, "income_level"], df.at[i, "income_level_unresolved"] = inc_wb, unres or None
                df.at[i, "income_level_source"] = f"World Bank API classification, accessed {wb_date} (Taiwan = High income override)"
            for rid, mrow in meta.items():
                if rid in back_ok:
                    i = df.index[df["record_id"] == rid][0]
                    for c in META_COLS:
                        df.at[i, c] = mrow.get(c)
                    df.at[i, "metadata_source"] = "hta_v2_5_harvest_2026-10-13"
                    df.at[i, "mesh_terms_source"] = "openalex_mesh"
        df["extracted"] = df["extracted"].astype(object)
        df.loc[df["record_id"].isin(x.index), "extracted"] = True
        return df

    ads5, inc5 = apply(ads, True), apply(inc, False)

    # topic placement (2026-10-14): the re-included records were not in the fitted topic model;
    # make_hff_topic_coordinates_v2_5.py places them by nearest neighbours. When that file exists,
    # their topic_cluster_id / _label / _terms / _n come from it, and topic_placement records how
    # every included study got its cluster ("fitted" or "nearest-neighbour, k=15").
    tc = FI / "hff_topic_coordinates_v2_5.csv"
    if tc.exists():
        coords = pd.read_csv(tc, dtype={"record_id": str, "topic_cluster_id": str})
        place = coords.set_index("record_id")
        lab = ads5.dropna(subset=["topic_cluster_id"]).drop_duplicates("topic_cluster_id").set_index(
            ads5.dropna(subset=["topic_cluster_id"]).drop_duplicates("topic_cluster_id")["topic_cluster_id"].astype(str))
        for f in (ads5, inc5):
            f["topic_placement"] = f["record_id"].map(place["topic_placement"])
            mb = f["record_id"].isin(back_ok) & f["record_id"].isin(place.index)
            cid = f.loc[mb, "record_id"].map(place["topic_cluster_id"])
            f["topic_cluster_id"] = f["topic_cluster_id"].astype(object)
            f.loc[mb, "topic_cluster_id"] = cid.values
            f.loc[mb, "topic_cluster_label"] = f.loc[mb, "record_id"].map(place["topic_cluster_label"]).values
            for col in ("topic_cluster_terms", "topic_cluster_n"):
                if col in f.columns and col in lab.columns:
                    f[col] = f[col].astype(object)
                    f.loc[mb, col] = cid.map(lab[col]).values
    h = pd.read_csv(HEE, dtype={"record_id": str}, usecols=["record_id", "is_eligible"])
    hee = set(h.loc[h["is_eligible"] == True, "record_id"])  # noqa: E712
    for f in (ads5, inc5):
        f["also_in_hee"] = f["analysis_include"] & f["record_id"].isin(hee)
    assert (ads5["analysis_include"].values == inc5["analysis_include"].values).all()
    ai5 = ads5[ads5["analysis_include"]]
    assert ai5["extracted"].fillna(False).astype(bool).all(), "an included study is not extracted"

    # PRISMA: move re-included records from the no-function line to INCLUDED, per route
    pr = json.loads(IN_PRISMA.read_text(encoding="utf-8"))
    for o, n in ads5[ads5["record_id"].isin(back_ok)]["origin"].value_counts().items():
        lines = pr["routes"][o]["lines"]
        lines["no_financing_function_at_relabel"] -= n
        lines["INCLUDED"] += n
    pr["excluded"]["no_financing_function_at_relabel"] -= len(back_ok)
    pr["included"] = int(ads5["analysis_include"].sum())
    pr["included_by_route"] = {o: v["lines"].get("INCLUDED", 0) for o, v in pr["routes"].items()}
    pr["generated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pr["script"] = "projects/hff/final_includes/build_final_includes_v2_5.py"
    pr["identity"] += "; v2.5 moves Decision 17 HTA records from no_financing_function_at_relabel to INCLUDED"
    assert pr["included"] + sum(pr["excluded"].values()) == pr["pool_total"]
    for o, v in pr["routes"].items():
        assert int((ads5["origin"].eq(o) & ads5["analysis_include"]).sum()) == v["lines"]["INCLUDED"], o

    meta_out = {
        "generated_utc": pr["generated_utc"], "script": pr["script"],
        "included_v2_4": int(ads["analysis_include"].sum()), "included_v2_5": pr["included"],
        "hta_candidates_checked": 504, "hta_self_described": len(yes),
        "reincluded_hta": len(back_ok), "reincluded_by_origin": ads5[ads5["record_id"].isin(back_ok)]["origin"].value_counts().to_dict(),
        "reincluded_dup_doi": len(dup_doi), "reincluded_dup_title_year": len(dup_ty),
        "benefits_added_to_included": len(add), "reincluded_extracted_now": len(x),
        "benefits_decisions_included_v2_4": int(ads.loc[ads["analysis_include"], "func_list"].map(lambda v: v is not None and BEN in list(v)).sum()),
        "benefits_decisions_included_v2_5": int(ai5["func_list"].map(lambda v: v is not None and BEN in list(v)).sum()),
        "also_in_hee": int(ai5["also_in_hee"].sum()),
    }
    ads5.to_parquet(OUT_ADS, index=False)
    inc5.to_parquet(OUT_INC, index=False)
    OUT_PRISMA.write_text(json.dumps(pr, indent=1, ensure_ascii=False), encoding="utf-8")
    OUT_META.write_text(json.dumps(meta_out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(meta_out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
