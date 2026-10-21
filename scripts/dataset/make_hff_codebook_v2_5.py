#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""make_hff_codebook_v2_5.py -- data dictionary for the HFF v2.5 analysis dataset.

    python -X utf8 projects/hff/final_includes/make_hff_codebook_v2_5.py [--replace]

v2.5 copy (2026-10-13) of make_hff_codebook_v2_4.py: same logic and checks; inputs, output name and
expected counts changed, and the descriptions updated for v2.5 (Decision 17 applied: HTA records
are Benefits decisions; new columns `hta_decision17`, `financing_function_v52_pre_hta`,
`also_in_hee`, `topic_placement`). Companion file: hff_topic_coordinates_v2_5.csv (all 53,414
included studies: 53,365 fitted + 49 HTA records placed by nearest neighbours, 2026-10-14).
The v2.1-v2.4 scripts and dictionaries are untouched.

Writes `HFF_DATA_DICTIONARY_v2_5.md` next to this script: every column of
`hff_analysis_dataset_v2_5.parquet` with its type, % present among ALL rows (70,230) and among the
INCLUDED studies (`analysis_include`, 53,414), the number of distinct values and a description.
A second section covers the 15 columns that exist only in the record table
(`hff_includes_final_v2_5.parquet`).

FAILS (exit 1) if any column has no description, or if a description names a column that is not in
the data, so the dictionary cannot silently fall behind the dataset.

"Present" = not null, not an empty string, and not one of the literal missing sentinels this
corpus uses (`NA`, `Could not find`, `None`, `nan`); an array cell is present when non-empty.
Local only: no API calls. Refuses to overwrite an existing dictionary unless --replace is passed
(it only ever writes its own output file).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE / "hff_analysis_dataset_v2_5.parquet"
RECORDS = HERE / "hff_includes_final_v2_5.parquet"
OUT = HERE / "HFF_DATA_DICTIONARY_v2_5.md"
COORDS = HERE / "hff_topic_coordinates_v2_5.csv"   # companion file (make_hff_topic_coordinates_v2_5.py)


def companion_section(a: pd.DataFrame, inc: pd.Series) -> list[str]:
    """Dictionary section for hff_topic_coordinates_v2_5.csv; every number is read from the file
    and checked against the analysis dataset (fails if the two disagree)."""
    c = pd.read_csv(COORDS, dtype={"record_id": str, "topic_cluster_id": str})
    ai = a.loc[inc, ["record_id", "topic_cluster_id", "topic_cluster_n", "topic_placement"]].copy()
    ai["record_id"] = ai["record_id"].astype(str)
    m = c.merge(ai, on="record_id", suffixes=("", "_ads"))
    if (set(c["record_id"]) != set(ai["record_id"]) or len(m) != len(c)
            or not c["record_id"].is_unique):
        raise SystemExit("hff_topic_coordinates_v2_5.csv does not match the included studies")
    if not (m["topic_cluster_id"] == m["topic_cluster_id_ads"].astype(str)).all():
        raise SystemExit("coordinate-file clusters differ from topic_cluster_id")
    if not (m["topic_placement"] == m["topic_placement_ads"]).all():
        raise SystemExit("coordinate-file topic_placement differs from the dataset")
    fitted = int((c["topic_placement"] == "fitted").sum())
    placed = len(c) - fitted
    cl = m[m["topic_cluster_id"] != "-1"]
    size = cl.groupby("topic_cluster_id").size()
    n_diff = int((size != cl.groupby("topic_cluster_id")["topic_cluster_n"].first()).sum())
    noise = int((c["topic_cluster_id"] == "-1").sum())
    pl = c[c["topic_placement"] != "fitted"]
    return [
        "## Companion file: `hff_topic_coordinates_v2_5.csv`",
        "",
        f"One row per included study ({len(c):,}), joinable on `record_id`: {fitted:,} positioned by "
        f"the fitted topic model and {placed:,} (the Decision 17 HTA records) placed into the same map "
        "by nearest neighbours. Written by `make_hff_topic_coordinates_v2_5.py`; copied into the team "
        "export and the share folder. It holds the positions behind the topic maps drawn by "
        "`projects/hsf/analysis/R/fig-topicmap_v3.R` and `fig-topicmap-financing_v3.R` "
        "(`figures/fig_topicmap_v2_5.png`, `fig_topicmap_sizes_v2_5.png`, "
        "`fig_topicmap_financing_v2_5.png`). It supersedes `hff_topic_coordinates_v2_4.csv` "
        "(the 53,365 fitted studies only); the fitted positions are identical in both.",
        "",
        "| column | description |",
        "|---|---|",
        "| `record_id` | EPPI-Reviewer record identifier, as in the analysis dataset. |",
        "| `x`, `y` | 2-D UMAP position of the study's title + abstract embedding (all-MiniLM-L6-v2) "
        "from the v3 topic model; for placed studies, the median position of their 15 nearest "
        "fitted neighbours. **For drawing only: UMAP positions are not distances**, and neither "
        "axis has a meaning. |",
        "| `topic_cluster_id` | HDBSCAN cluster, identical to `topic_cluster_id` in the dataset "
        f"(checked); `-1` = unclustered noise ({noise:,} studies, {100 * noise / len(c):.1f}%; "
        f"{int((pl['topic_cluster_id'] == '-1').sum())} of the {placed} placed). |",
        "| `topic_cluster_label` | c-TF-IDF label; `Unclustered (noise)` for `-1`. |",
        f"| `topic_placement` | `fitted` ({fitted:,}) or `nearest-neighbour, k=15` ({placed:,}); "
        "identical to the dataset column. |",
        "",
        "**Provenance and caveats.** The model (`projects/hsf/analysis/R/05-topic-model_v3.py`) was "
        "**fitted on the 53,782 studies included in v2.3**, before the v2.4 DOI de-duplication, and "
        "was not refitted. The 53,365 fitted v2.5 studies keep the position and cluster they were "
        f"fitted with. The {placed} studies re-included by Decision 17 were not in the fit and were "
        "**placed** (L. Sempe, 2026-10-14): embedded with the same model, matched to their 15 nearest "
        "fitted v2.4 studies by cosine similarity, positioned at the neighbours' median coordinates "
        "and given the neighbours' most common cluster (ties: the nearer neighbour). No fitted point "
        "or cluster moves. Cluster sizes from the fit (`topic_cluster_n`, `topic_labels_v3.csv`) "
        f"count the 53,782: **recount them on the {len(c):,}** for any v2.5 figure or table (they "
        f"differ for {n_diff} of the {len(size)} clusters; on the {len(c):,} the clusters hold "
        f"{size.min():,} to {size.max():,} studies).",
        "",
    ]

SENTINELS = {"", "NA", "Could not find", "None", "nan"}
EXPECTED_ROWS, EXPECTED_INCLUDED = 70_230, 53_414

# column -> (group, description). Order within a group is the order of the table.
DESC: dict[str, tuple[str, str]] = {
    # ---- identity
    "record_id": ("Identity and route", "EPPI-Reviewer record identifier (unique per row). Joins every HFF file."),
    "year": ("Identity and route", "Publication year from the corpus (2010-2026; 2026 is a partial year). Null for 5 rows (132855712, 132855713, 132855714 included; 131704457, 132780287 excluded)."),
    "title": ("Identity and route", "Title from the corpus."),
    "abstract": ("Identity and route", "Abstract from the corpus. **The literal string `NA` means no abstract** (4,728 rows: the 4,715 `no_abstract` exclusions and 13 of the 44 `hee_code_no_include_majority` exclusions, which take that earlier reason); every included study has a real abstract."),
    "origin": ("Identity and route", "The PRISMA route the record entered by: `v1_include` (September include set, 36,017 rows), `v11.2_rescreen` (October targeted re-screen, prompt v11.2, 6,987), `unsure_original_screening` (production screening's EXCLUDE_UNSURE_TA records sent forward under Decision 11b, 23,663), `pass2_unsure` (v2.2: pass-1 includes the September pass-2 re-screen judged EXCLUDE_UNSURE_TA, sent forward under Decision 11b, 2,199), `dropped_before_pass2` (v2.2: pass-1 include verdicts absent from the pass-2 input file with no documented rule, 1,364). Provenance; not an analysis group."),
    "pathways": ("Identity and route", "Constant `HSF` (legacy from the v1 extraction file; set for the October additions harvested in v2.3, i.e. those included in v2.3); null for 64 v1 rows and the other excluded October rows. No information."),
    # ---- inclusion
    "analysis_include": ("Inclusion and exclusion", "**TRUE for the 53,414 included studies. Filter on this for every analysis.**"),
    "exclusion_reason_v2": ("Inclusion and exclusion", "Why a row is not included; null when included. `hee_code_no_include_majority` (v2.2, first reason, ruling L. Sempe 2026-10-13: the 44 `dropped_before_pass2` rows admitted at pass 1 only by the HEE-arm code `INCLUDE_TA` with no majority include vote; 11 had been included before the ruling), `no_abstract` (Decision 11b), `no_financing_function_at_relabel` (Decision 13: neither second-opinion model found a verified function; in v2.5 the 49 such records that describe themselves as an HTA are included instead, Decision 17), `duplicate` (same study as a kept record), `placeholder` (placeholder or series title), `no_v52_label_not_extracted` (panel returned no label and never extracted; 19 rows), `not_screenable_or_extractable` (132866029), `second_opinion_unresolved` (131629183, 132415273), `duplicate_doi` (v2.4, last reason, Decision 16: 417 included-in-v2.3 records that share a normalised DOI with a kept included record: 414 with a similar title, difflib ratio >= 0.80, and 3 by a manual ruling of L. Sempe on pairs whose titles differ; see `duplicate_doi_of`), and `v1_excluded:placeholder` / `v1_excluded:contradicts_own_rationale` (the 51 v1 rows that never entered the pool)."),
    "duplicate_doi_of": ("Inclusion and exclusion", "v2.4 (Decision 16): for the 417 `duplicate_doi` rows, the record_id of the kept included record that shares the normalised DOI (keep order v1 > re-screen > original-unsure > pass2_unsure > dropped_before_pass2, then lowest record_id); null otherwise."),
    "analysis_include_v1": ("Inclusion and exclusion", "The September (v1) counting flag: TRUE for the 35,966 v1 analysis includes, FALSE for the 51 v1 rows outside them; null for the October additions. History only."),
    "placeholder": ("Inclusion and exclusion", "1 = placeholder or series title (for example \"Essays in ...\"), by v1's rule in `R/00-build-base.py`; 0 otherwise. No included study is a placeholder."),
    "extracted": ("Inclusion and exclusion", "TRUE when the record carries the extracted non-financing fields (for v1, either extraction run; for the October additions, all three field groups returned). TRUE for every included study."),
    # ---- function label
    "financing_function_v52": ("Financing function (codebook v52)", "**The function label used for analysis.** One or more of the 8 financing functions or `Overall`, joined with `;` (no space). v2.5 (Decision 17): for the 188 included records that describe themselves as an HTA (`hta_decision17`), `Benefits decisions` is listed first (it becomes `primary_function`), the earlier functions after it; the 49 re-included HTA records carry `Benefits decisions` only. The pre-rule label is `financing_function_v52_pre_hta`. From the panel re-label (Claude Sonnet 5 + DeepSeek V4 Pro coding blind, GLM-5.2 adjudicating), or, when `function_label_source` = `second_opinion`, the union of the verified functions found by GPT-5.6-sol and Gemini 3.1 Pro (Decision 13). Empty for Decision 13 exclusions."),
    "hta_decision17": ("Financing function (codebook v52)", "v2.5 (Decision 17): TRUE for the 188 included records that describe themselves as a health technology assessment (deepseek-v4.1-flash judgment with a verified self-describing quote, `hta_check_v2_5.py`, among 504 candidates with an HTA term): 49 re-included from `no_financing_function_at_relabel` and 139 included ones that gained `Benefits decisions`. FALSE otherwise."),
    "financing_function_v52_pre_hta": ("Financing function (codebook v52)", "The v52 function label before Decision 17 was applied (`;`-joined). Equal to `financing_function_v52` except for the 188 `hta_decision17` records; empty for the 49 re-included ones, which had no function."),
    "also_in_hee": ("Identity and route", "v2.5: TRUE when the included study is also included in the HEE arm (HEE v2, 41,657 full economic evaluations; `is_eligible` in `projects/hee/analysis/data/hee_analysis_master.csv`): 1,874 included studies. FALSE for every excluded row. **Report the two arms separately with the overlap stated; never sum their counts** (Decision 17, point 2)."),
    "func_list": ("Financing function (codebook v52)", "`financing_function_v52` split into a list (array in parquet; `; `-joined in the CSV export)."),
    "primary_function": ("Financing function (codebook v52)", "First function listed in `financing_function_v52` (v1's rule). The order is the coder's, not a ranking of importance; prefer `func_list` for counts."),
    "n_functions": ("Financing function (codebook v52)", "Number of functions in `func_list` (0-7). 0 for the 4 included studies without a label."),
    "labelled": ("Financing function (codebook v52)", "TRUE when `n_functions` > 0."),
    "function_label_source": ("Financing function (codebook v52)", "**Quality flag.** `panel` (46,063 included), `hta_rule_decision17` (49 included: excluded for no function until v2.5, re-included by Decision 17 with `Benefits decisions`; their `label_route`, `panel_label_v52` and `second_opinion_decision` keep the earlier no-function history), `second_opinion` (7,298 included: the panel found no function, the second-opinion check kept the record and supplied the label; validation found these over-tag PFM and only ~60% are expected to be genuine HFF studies), `none_panel_returned_no_label` (4 included v1 studies). Excluded rows also carry `panel_no_function` and `panel_no_function_check_unresolved`. **Run every function result with and without `second_opinion`.**"),
    "label_route": ("Financing function (codebook v52)", "How the panel reached its label: `agreed` (both coders gave the same set), `adjudicated` (GLM-5.2 resolved a disagreement), `missing` (no label after retries)."),
    "label_adj_confidence": ("Financing function (codebook v52)", "Adjudicator's stated confidence (`high` / `low`) for adjudicated records; empty string for agreed records."),
    "panel_label_v52": ("Financing function (codebook v52)", "The panel's own label before Decision 13. `Other` or `Unclear` for the records sent to the second-opinion check."),
    "second_opinion_decision": ("Financing function (codebook v52)", "Decision 13 outcome on the panel's no-function records: `keep` (at least one second-opinion model found a verified function), `exclude` (both found none), `missing` (131629183, 132415273: one model returned no valid verdict). Null for records the panel labelled."),
    "second_opinion_models": ("Financing function (codebook v52)", "Which second-opinion model(s) found a function: `gpt-5.6-sol`, `gemini-3.1-pro` or both (`;`-joined). Empty string for panel-labelled records."),
    "financing_function_v41": ("Financing function (codebook v52)", "The superseded September label (single-model GLM-5.2 extraction, codebook v41), renamed from `financing_function_final`. v1 rows only. Do not mix with v52."),
    # ---- screening
    "screening_generation": ("Screening", "**Provenance only, not an analysis flag** (team ruling 2026-10-13). Which screening pass put the record in: `pod_run_2026-09-18` (v9.8), `v99_rescreen_2026-09-27` (v9.9), `prior_partial_2026-09-17` (earlier partial pass), `reinstatement_2026-09-29`, `v11.2_targeted_rescreen_2026-10-08`, `unsure at original screening (Decision 11b)`, and for the v2.2 gap routes `pass-1 include, unsure at September pass-2 re-screen (gap, 2026-10-13)` and `pass-1 include, absent from the pass-2 input file (gap, 2026-10-13)`."),
    "screening_file": ("Screening", "Source file of the screening verdict for the October additions: `results_hsf_FINAL.jsonl` (production pass 1: the original-unsure and `dropped_before_pass2` routes), `results_pilot3000_v11_2.jsonl`, `results_remaining_36259.jsonl` (re-screen), `results_hff_final.jsonl` / `results_v99_final.jsonl` (September pass 2, v9.8 run with the v9.9 overlay winning: the `pass2_unsure` route); null for v1 rows."),
    "screening_code": ("Screening", "Screening code that admitted the record: `INCLUDE_HSF`, `INCLUDE_HSF_REVIEW`, `EXCLUDE_UNSURE_TA` (could not judge; IN under Decision 11b), `MODEL_ERROR` (no usable run; fail-safe include) or `INCLUDE_TA` (44 `dropped_before_pass2` rows, none included: the production runner's plurality code was `INCLUDE_TA`, an HEE-arm code that some runs emitted under the HSF prompt, and prefix matching made it an include; none of the 44 has a majority include vote (vote share 0 for 39, 1/3 for 5), so all 44 are excluded as `hee_code_no_include_majority`)."),
    "screening_decision": ("Screening", "`INCLUDE` or `EXCLUDE` as the runner recorded it. `EXCLUDE` here always means the unsure code, which Decision 11b sends forward; it is not an exclusion."),
    "ta_unsure": ("Screening", "TRUE when the admitting verdict was `EXCLUDE_UNSURE_TA` (14,937 included: 12,635 from the original screening + 1,172 from the re-screen + 1,130 from the September pass 2). Provenance; not an analysis group."),
    "hsf_include": ("Screening", "Constant 1 (every row entered as an HSF include or an 11b IN record). No information."),
    "screened": ("Screening", "Constant 1. No information."),
    "screening_explanation_source": ("Screening", "Which run the stored explanation comes from: `final_include_run`, `final_non_include_run`, `prior`, `reinstatement`, `original_unsure_run`, `v11.2_include_run`, `v11.2_unsure_run`, `v11.2_no_usable_run`, and for the v2.2 gap routes `pass2_unsure_run`, `original_include_run`, `original_no_usable_run` (no run carried an include code; the first run's explanation is stored)."),
    "screening_explanation": ("Screening", "The screening model's rationale (free text) for the admitting verdict."),
    "screening_n_runs": ("Screening", "Usable screening runs behind the verdict (0-3; k=3). 0 = fail-safe include with no usable run; null for reinstatements."),
    "screening_vote_share_include": ("Screening", "Share of usable runs voting include (0, 1/3, 1/2, 2/3, 1). 0 for unsure records is expected: the unsure code counts as a non-include vote."),
    "screening_model_agreement": ("Screening", "Constant `agree` (single primary model). No information."),
    "screening_flag": ("Screening", "v1 diagnostic: `fail_safe` (included with no usable run; 64 included), `contradicts_own_rationale` (none included), or empty."),
    "reinstated": ("Screening", "1 when the 2026-09-29 reinstatements (Decision 7 guard re-check or manual review), not a screening run, put a v1 record in."),
    "reinstatement_reason": ("Screening", "`guard_recheck_2026-09-29`, `manual_review_quarantined_includes_2026-09-29` or `manual_review_reimbursement_drops_2026-09-29`; empty otherwise. v1 rows only."),
    # ---- September-only flags
    "governance_flag": ("September-only flags (describe the old v41 labels; v1 rows only)", "Stage-0 bucket consensus said Governance - PFM (Counting rule 3). Computed against the v41 pipeline; null for the October additions. Do not cross with v52 functions without saying so."),
    "overall_flag": ("September-only flags (describe the old v41 labels; v1 rows only)", "Stage-0 consensus said Overall. Superseded by the v52 `Overall` label; v1 rows only."),
    "pfm_subtype": ("September-only flags (describe the old v41 labels; v1 rows only)", "`core` / `budget_impact` / `other` for v41 PFM-labelled records. **Retired by Decision 8 (2026-10-02); do not use for reporting.**"),
    "oop_role": ("September-only flags (describe the old v41 labels; v1 rows only)", "Decision 1 out-of-pocket role (`protection` / `source` / `both` / `none`), derived from text for v1 includes. Decision 9 Q3 superseded the rule it served."),
    "total_calls": ("September-only flags (describe the old v41 labels; v1 rows only)", "v41 extraction status: calls made (constant `4`). v1 rows only."),
    "has_error": ("September-only flags (describe the old v41 labels; v1 rows only)", "v41 extraction status: error flag (constant `0`). v1 rows only."),
    "outcome_domain_final_master": ("September-only flags (describe the old v41 labels; v1 rows only)", "The v41 master's outcome domain, kept so the disagreement with the adopted v48 value stays countable (they agree on 67% of v1 records). Not for analysis."),
    "study_design_final_master": ("September-only flags (describe the old v41 labels; v1 rows only)", "The v41 master's study design (fallback copy; see EXTRACTION_RECONCILE.md). Not for analysis."),
    "geo_final_master": ("September-only flags (describe the old v41 labels; v1 rows only)", "The v41 master's geography (fallback copy). Not for analysis."),
    "dedupe_group": ("September-only flags (describe the old v41 labels; v1 rows only)", "v1 de-duplication group (exact lower-cased title). v1 rows only; superseded by `dedupe_group_v2`."),
    "dedupe_group_size": ("September-only flags (describe the old v41 labels; v1 rows only)", "Size of the v1 dedupe group. v1 rows only."),
    # ---- bibliographic (v1 only)
    "doi": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "DOI from CrossRef title matching (v1 rule: title similarity, +5 same year, -15 if more than 2 years apart, minimum score 82). Present for 78.9% of the 53,414 included studies (74.7% of the 20,417 included October additions). **v2.4 de-duplicates on it** (Decision 16): of the 394 DOIs that v2.3 showed shared by 815 included rows, 414 copies with a similar title were excluded as `duplicate_doi`, plus 3 whose titles differ but which L. Sempe ruled the same work (417); 4 DOIs (8 included rows) stay shared, ruled separate studies, most likely wrong DOI matches by title search (`dedupe_doi_review_v2_4.csv`)."),
    "doi_confidence": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "CrossRef title-match score behind the DOI (0-100)."),
    "biblio_source": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Where the bibliographic fields came from: `crossref+openalex`, `crossref`, or `no_doi`. Null for 64 included v1 rows."),
    "authors": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Author list (CrossRef)."),
    "journal": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Journal or container title (CrossRef)."),
    "volume": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Volume (CrossRef)."),
    "issue": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Issue (CrossRef)."),
    "pages": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Pages (CrossRef)."),
    "url": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Landing URL (CrossRef). `Could not find` is a missing sentinel."),
    "publisher_location": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Publisher location (CrossRef); mostly `Could not find`."),
    "research_funder": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Funder(s) (CrossRef)."),
    "language": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "ISO language code (CrossRef); `Could not find` is a missing sentinel."),
    "language_source": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "`crossref` or `no_doi`."),
    "author_keywords": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Constant `Could not find`: empty in effect."),
    "author_affiliation_institutions": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Author affiliation institutions (OpenAlex)."),
    "author_affiliation_countries": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Author affiliation countries (OpenAlex). Not used for study geography."),
    "keywords_openalex_generated": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "OpenAlex-generated keywords."),
    "ml_topics": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "OpenAlex topics."),
    "ml_thematic_cluster": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "OpenAlex domain / field / subfield of the primary topic."),
    "mesh_theme": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "MeSH headings or OpenAlex concepts as fallback, `; `-joined (`derive_mesh_theme.derive_theme`). For v1 rows the headings came from PubMed; for the October additions from the OpenAlex work record, which carries PubMed's MeSH, because PubMed refused connections on 2026-10-13 (`mesh_terms_source`)."),
    "mesh_source": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "`pubmed` (MeSH headings found), `openalex_fallback` (OpenAlex concepts used instead) or `none`. For the October additions `pubmed` means MeSH headings read from OpenAlex, not a PubMed call (see `mesh_terms_source`). Null for 296 included v1 rows."),
    "is_oa": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Open-access status (OpenAlex): from the September enrichment for v1 rows, the 2026-10-13 harvest for the October additions."),
    "oa_url": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Open-access URL where one was found."),
    # ---- topic model
    "topic_cluster_id": ("Topic model (v3 refit on the included studies)", "Topic cluster from the v3 model, **refitted on the 53,782 included studies** (`projects/hsf/analysis/R/05-topic-model_v3.py`: all-MiniLM-L6-v2 embedding of title + abstract, UMAP 2D, HDBSCAN, c-TF-IDF labels; same mechanism, seed and settings as v2). Fitted on the v2.3 included set (53,782), before the DOI de-duplication, so the 417 `duplicate_doi` rows also carry a cluster; null for every other row outside the included set. The 49 studies re-included in v2.5 (Decision 17) were not in the fit and were **placed** by nearest neighbours (`topic_placement`), so every included study has a cluster. 56 clusters plus `-1` (HDBSCAN noise; 13,612 of the 53,414 v2.5 included studies, 25.5%, 16 of them placed). Ids and labels differ from v2 (kept as `topic_cluster_*_v2`)."),
    "topic_placement": ("Topic model (v3 refit on the included studies)", "v2.5 (2026-10-14): how the study got its topic position and cluster. `fitted` (53,365 included studies: in the v3 fit) or `nearest-neighbour, k=15` (the 49 Decision 17 HTA records, not in the fit: embedded with the same model, positioned at the median of their 15 nearest fitted v2.4 studies by cosine similarity, cluster = the neighbours' most common cluster). Null for rows outside the included set (the 417 `duplicate_doi` rows keep the cluster they were fitted with)."),
    "topic_cluster_label": ("Topic model (v3 refit on the included studies)", "Cluster label (top c-TF-IDF terms); `Unclustered (noise)` for cluster -1."),
    "topic_cluster_terms": ("Topic model (v3 refit on the included studies)", "Distinctive terms of the cluster; null for noise."),
    "topic_cluster_n": ("Topic model (v3 refit on the included studies)", "Number of studies in the cluster in the v3 fit (on the 53,782 v2.3 included studies, so it can exceed the count among v2.4 included studies by the cluster's `duplicate_doi` rows)."),
    "topic_cluster_id_v2": ("Topic model (v3 refit on the included studies)", "The v2 topic cluster (fitted on the 52,826 pass-1 confident includes, 2026-09), kept for comparison; v1 rows only. Superseded by `topic_cluster_id`; ids are not comparable."),
    "topic_cluster_label_v2": ("Topic model (v3 refit on the included studies)", "Label of the v2 cluster. History only."),
    "topic_cluster_terms_v2": ("Topic model (v3 refit on the included studies)", "Distinctive terms of the v2 cluster. History only."),
    "topic_cluster_n_v2": ("Topic model (v3 refit on the included studies)", "Size of the v2 cluster in the v2 corpus run. History only."),
    "metadata_source": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Which harvest supplied the row's bibliographic metadata: `v1_harvest_2026-09` (every v1 row) or `october_harvest_2026-10-13` (the 20,795 October additions included in v2.3, `enrich_metadata_v2_2.py`: one CrossRef search per record plus an OpenAlex DOI lookup; 417 of them are now `duplicate_doi` exclusions). `hta_v2_5_harvest_2026-10-13` (the 39 October-origin HTA records re-included in v2.5, `hta_metadata_v2_5.py`, same harvest function). Null for the other October rows, which were not harvested."),
    "mesh_terms_source": ("Bibliographic metadata (v1 rows: September 2026 harvest; included October additions: 2026-10-13 harvest)", "Where the MeSH headings behind `mesh_theme` were read: `pubmed` (v1 rows, PubMed E-utilities) or `openalex_mesh` (October additions, from the OpenAlex work record). Set by origin: it is `pubmed` for every v1 row, including the 19,683 whose `mesh_source` is `openalex_fallback` or `none`, so read it together with `mesh_source`."),
    # ---- extraction
    "type_of_analysis_stated_final": ("Extracted study fields (GLM-5.2)", "Type of analysis as STATED by the authors (`Quantitative` / `Qualitative` / `Mixed methods`). Null when the abstract does not state it, which is most records; use `type_of_analysis_deduced_final` for coverage."),
    "type_of_analysis_stated_split": ("Extracted study fields (GLM-5.2)", "Disagreement flag from the multi-model design; constant 0 (single model)."),
    "type_of_analysis_stated_reasoning": ("Extracted study fields (GLM-5.2)", "Model's justification for the stated type."),
    "type_of_analysis_deduced_final": ("Extracted study fields (GLM-5.2)", "Type of analysis deduced by the model: `Quantitative` / `Qualitative` / `Mixed methods`."),
    "type_of_analysis_deduced_split": ("Extracted study fields (GLM-5.2)", "Constant 0 (single model)."),
    "type_of_analysis_deduced_reasoning": ("Extracted study fields (GLM-5.2)", "Model's justification."),
    "study_design_final": ("Extracted study fields (GLM-5.2)", "Study design, one of 13 categories (for example `Cross-sectional and correlational analyses`, `Policy and implementation analyses`, `Experimental and quasi-experimental impact evaluations`, `Reviews of studies`)."),
    "study_design_split": ("Extracted study fields (GLM-5.2)", "Constant 0 (single model)."),
    "study_design_reasoning": ("Extracted study fields (GLM-5.2)", "Model's justification."),
    "data_type_final": ("Extracted study fields (GLM-5.2)", "`Cross-sectional data`, `Time-series / longitudinal`, `Panel data`, `Qualitative data`, `Mixed data types`. Thin for the unsure route (61%)."),
    "data_type_split": ("Extracted study fields (GLM-5.2)", "Constant 0 (single model)."),
    "data_type_reasoning": ("Extracted study fields (GLM-5.2)", "Model's justification."),
    "data_source_final": ("Extracted study fields (GLM-5.2)", "Main data source, one of 11 categories (`Administrative data`, `Primary survey data`, `National / international survey datasets`, ...). Thin for the unsure route (40%)."),
    "data_source_split": ("Extracted study fields (GLM-5.2)", "Constant 0 (single model)."),
    "data_source_reasoning": ("Extracted study fields (GLM-5.2)", "Model's justification."),
    "unit_of_observation_final": ("Extracted study fields (GLM-5.2)", "Unit of observation, one of 9 categories (`Individual / person`, `Organisation / institution`, `Programme / intervention`, `Country`, ...)."),
    "unit_of_observation_split": ("Extracted study fields (GLM-5.2)", "Constant 0 (single model)."),
    "unit_of_observation_reasoning": ("Extracted study fields (GLM-5.2)", "Model's justification."),
    "outcome_domain_final": ("Extracted study fields (GLM-5.2)", "Health-system outcome domain(s), `; `-joined: `Financial protection`, `Efficiency in the use of resources`, `Equitable distribution of health system resources`, `Improved level and distribution of health`, `Quality of service provision`, `Responsiveness to citizens`, `Transparency and accountability`, `Economic development`, `Other`, `Unclear`. v1 values are the v48 coder generation (EXTRACTION_RECONCILE.md). Thin for the unsure route (66%)."),
    "outcome_domain_split": ("Extracted study fields (GLM-5.2)", "Constant 0 (single model)."),
    "outcome_domain_reasoning": ("Extracted study fields (GLM-5.2)", "Model's justification; the text the v1 `outcome_other_theme` clustering was built from."),
    "outcome_other_theme": ("Extracted study fields (GLM-5.2)", "Theme(s) of an `Other` outcome. **Built two ways:** for v1 rows by clustering the reasoning text (`Not applicable` when the domain has no `Other`, `Not clustered` for HDBSCAN noise); for the October additions by the LLM field (v49 definition; `Other outcome (none of these themes)`). Do not pool without saying so."),
    "outcome_other_theme_source": ("Extracted study fields (GLM-5.2)", "How `outcome_other_theme` was assigned: a cluster id, `mixed cluster 12, split by keywords...`, HDBSCAN noise, `no 'Other' in outcome_domain` (v1 rows), or `llm_field_v52_extraction` (October additions)."),
    # ---- geography and income
    "geo_final": ("Geography and income", "Country or countries the study covers, comma-separated, or a region / `Global` / `Multiple`. Extracted from the abstract (GLM-5.2)."),
    "geo_split": ("Geography and income", "Constant 0 (single model)."),
    "geo_reasoning": ("Geography and income", "Model's justification for the geography."),
    "continent": ("Geography and income", "**World Bank region(s)**, not continents (for example `Sub-Saharan Africa`, `Europe and Central Asia`), `; `-joined; derived from `geo_final` by `enrich_geo` (`projects/hsf/scripts/run_hsf_extraction_29sept.py`)."),
    "income_level": ("Geography and income", "**World Bank income group** (`Low income`, `Lower middle income`, `Upper middle income`, `High income`) per named country, `; `-joined for multi-country studies in the order named. World Bank API file accessed 2026-09-04; Taiwan = High income by override. **This is the CURRENT (FY2027) classification, not the classification in the year of publication.**"),
    "income_level_source": ("Geography and income", "Provenance of `income_level` (constant string naming the WB API file, access date and the Taiwan override)."),
    "income_level_unresolved": ("Geography and income", "Country or region tokens in `geo_final` that could not be matched to a World Bank economy (regions, `Low and middle-income countries`, ...)."),
    "income_level_bundled": ("Geography and income", "The previous income value from the bundled lookup (`wb_reference_lookup.py`): `HIC` / `MIC` (= upper middle) / `LMIC` / `LIC`, **classification in the publication year**. Kept for year-specific analyses; not the default."),
    "fcas": ("Geography and income", "Named countries on the fragile and conflict-affected list, from the bundled lookup via `enrich_geo`."),
    "geo_derivation_note": ("Geography and income", "Note from `enrich_geo` when a geography value is a region, multi-region or non-place descriptor."),
    # ---- dedupe v2
    "dedupe_group_v2": ("De-duplication (v2.2)", "record_id of the kept copy of the record's study (DOI, or normalised title + same year, titles of 4+ words). Keep rule: v1 over re-screen over original-unsure over pass2_unsure over dropped_before_pass2 (the two v2.2 gap routes last, so no v2.1 keep/drop decision changes); then a record with a DOI; then the lowest record_id. Null for rows excluded before de-duplication."),
    "dedupe_group_size_v2": ("De-duplication (v2.2)", "Number of records in the v2.2 duplicate group (1-3)."),
    "dedupe_match": ("De-duplication (v2.2)", "How the group was matched: `title_year` (all 467 groups) or empty for singletons."),
}

# Columns present only in the record table (hff_includes_final_v2_5.parquet), not in the analysis dataset.
DESC_RECORDS_ONLY: dict[str, str] = {
    "pfm_basis": "v1 only, v41 label: the evidence behind a PFM label (`budget_impact`, `core_subgroup`, `payer_cost`, `unclassified`). Superseded by Decision 8.",
    "pfm_core_source": "v1 only, v41 label: the vocabulary sub-group or `terms` that made a PFM record `core`.",
    "basis_Benefits": "v1 only, v41 label: `terms` when mechanism vocabulary supports the Benefits label, `unstated` when the label has no stated basis.",
    "basis_Purchasing": "v1 only, v41 label: as `basis_Benefits`, for Purchasing.",
    "basis_PFM": "v1 only, v41 label: as `basis_Benefits`, for PFM.",
    "basis_Revenue": "v1 only, v41 label: as `basis_Benefits`, for Revenue Raising.",
    "basis_Pooling": "v1 only, v41 label: as `basis_Benefits`, for Pooling.",
    "basis_SupplyChain": "v1 only, v41 label: as `basis_Benefits`, for Supply chain.",
    "basis_CapInfra": "v1 only, v41 label: as `basis_Benefits`, for Capital: infrastructure.",
    "basis_CapInputs": "v1 only, v41 label: as `basis_Benefits`, for Capital: other inputs.",
    "basis_n_unstated": "v1 only, v41 label: number of the record's functions with no stated basis.",
    "revenue_raising_sub1_final": "v1 only, v41 extraction: revenue sub-option 1 (`Yes` / `No` / `Unclear` / `Not applicable`).",
    "revenue_raising_sub1_type_final": "v1 only, v41 extraction: type of the revenue source for sub-option 1 (for example `External/donor`, `Non-governmental mechanism`).",
    "revenue_raising_sub1_justification_final": "v1 only, v41 extraction: justification for sub-option 1.",
    "revenue_raising_sub2_final": "v1 only, v41 extraction: revenue sub-option 2 (`Yes` / `No` / `Unclear` / `Not applicable`).",
}


def _flat(v):
    if isinstance(v, (list, tuple, np.ndarray)):
        return "; ".join(map(str, v))
    return v


def present(s: pd.Series) -> pd.Series:
    """Boolean mask: value present (not null, not empty, not a missing sentinel; arrays non-empty)."""
    if s.dtype == object:
        def ok(v):
            if v is None:
                return False
            if isinstance(v, (list, tuple, np.ndarray)):
                return len(v) > 0
            if isinstance(v, float) and np.isnan(v):
                return False
            return str(v).strip() not in SENTINELS
        return s.map(ok).astype(bool)
    return s.notna()


def coverage(df: pd.DataFrame, inc: pd.Series) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        m = present(df[c])
        rows.append({
            "column": c,
            "type": str(df[c].dtype),
            "pct_present_all": round(100 * m.mean(), 1),
            "pct_present_included": round(100 * m[inc].mean(), 1),
            "n_distinct": int(df[c].map(_flat).nunique(dropna=True)),
        })
    return pd.DataFrame(rows)


def check_descriptions(cols: list[str], desc_keys: list[str], what: str) -> list[str]:
    errs = []
    missing = [c for c in cols if c not in desc_keys]
    stale = [c for c in desc_keys if c not in cols]
    if missing:
        errs.append(f"{what}: {len(missing)} column(s) have no description: {missing}")
    if stale:
        errs.append(f"{what}: {len(stale)} description(s) name a column not in the data: {stale}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", action="store_true", help="overwrite an existing dictionary")
    args = ap.parse_args()

    a = pd.read_parquet(ANALYSIS)
    r = pd.read_parquet(RECORDS)
    rec_only = [c for c in r.columns if c not in a.columns]
    errs = check_descriptions(list(a.columns), list(DESC), "analysis dataset")
    errs += check_descriptions(rec_only, list(DESC_RECORDS_ONLY), "record-table-only columns")
    if len(a) != EXPECTED_ROWS or int(a["analysis_include"].sum()) != EXPECTED_INCLUDED:
        errs.append(f"row counts changed: {len(a)} rows / {int(a['analysis_include'].sum())} included, "
                    f"expected {EXPECTED_ROWS} / {EXPECTED_INCLUDED}; update the docs before regenerating")
    if errs:
        print("DICTIONARY NOT WRITTEN:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    if OUT.exists() and not args.replace:
        print(f"{OUT.name} exists; pass --replace to regenerate it", file=sys.stderr)
        return 1

    inc = a["analysis_include"].astype(bool)
    cov = coverage(a, inc).set_index("column")
    rinc = r["analysis_include"].astype(bool)
    rcov = coverage(r[rec_only], rinc).set_index("column")

    L = []
    n_v1_inc = int((a.loc[inc, "origin"] == "v1_include").sum())
    L.append("# HFF v2.5 data dictionary")
    L.append("")
    L.append(f"Generated by `make_hff_codebook_v2_5.py` from `hff_analysis_dataset_v2_5.parquet` "
             f"({len(a):,} rows x {a.shape[1]} columns; **{int(inc.sum()):,} included studies**, "
             f"`analysis_include == TRUE`). Do not edit by hand: change the descriptions in the script "
             f"and regenerate. The script fails if any column has no description.")
    L.append("")
    L.append("**% present** = not null, not an empty string and not one of the literal missing sentinels "
             "`NA`, `Could not find`, `None`, `nan`; an array cell counts when non-empty. Two columns are "
             "given: among all rows (every record that entered the v2.2-v2.5 pool, plus the 51 v1 rows "
             "outside it) and among the included studies. Constant columns are flagged as carrying no "
             "information. Multi-valued fields are `; `-joined, except `financing_function_v52` / "
             "`financing_function_v52_pre_hta` (`;`, no space) and `geo_final` (comma-separated).")
    L.append("")
    L.append("Things to know before using any column: v2.5 has the same rows as v2.2-v2.4 and "
             f"{int(inc.sum()):,} included studies: v2.4's 53,365 plus 49 records that describe "
             "themselves as an HTA, re-included as Benefits decisions (Decision 17; `hta_decision17`). "
             "`also_in_hee` marks the 1,874 included studies also included in the HEE arm: report the "
             "arms separately and never sum them. The bibliographic and topic "
             f"columns cover every route ({int(inc.sum()) - n_v1_inc:,} included October additions). The September-only columns still exist for v1 rows only "
             f"(`origin == 'v1_include'`, {n_v1_inc:,} of the included, a cap of "
             f"{100 * n_v1_inc / int(inc.sum()):.1f}%). "
             "`function_label_source == 'second_opinion'` is a quality flag; `screening_generation` and "
             "`origin` are provenance only. See `../V2_5_DATASET_README.md`.")
    L.append("")
    L.append("**Metadata coverage among included studies, by route** (% present):")
    L.append("")
    meta_cols = ["doi", "journal", "authors", "language", "author_affiliation_countries",
                 "research_funder", "mesh_theme", "ml_topics", "topic_cluster_id"]
    routes = ["v1_include", "v11.2_rescreen", "unsure_original_screening", "pass2_unsure",
              "dropped_before_pass2"]
    ai_ = a[inc]
    L.append("| column | " + " | ".join(f"`{o}` (n={int((ai_['origin'] == o).sum()):,})" for o in routes)
             + " | all included |")
    L.append("|---|" + "---:|" * (len(routes) + 1))
    for c in meta_cols:
        cells = [f"{100 * present(ai_.loc[ai_['origin'] == o, c]).mean():.1f}" for o in routes]
        L.append(f"| `{c}` | " + " | ".join(cells) + f" | {100 * present(ai_[c]).mean():.1f} |")
    L.append("")
    groups: dict[str, list[str]] = {}
    for c in a.columns:
        groups.setdefault(DESC[c][0], []).append(c)
    for g, cols in groups.items():
        L.append(f"## {g}")
        L.append("")
        L.append("| column | type | % present all / included | distinct | description |")
        L.append("|---|---|---:|---:|---|")
        for c in cols:
            x = cov.loc[c]
            L.append(f"| `{c}` | {x['type']} | {x['pct_present_all']:.1f} / {x['pct_present_included']:.1f} "
                     f"| {x['n_distinct']:,} | {DESC[c][1]} |")
        L.append("")
    L.append("## Columns only in the record table (`hff_includes_final_v2_5.parquet`)")
    L.append("")
    L.append(f"These {len(rec_only)} columns are in the {r.shape[1]}-column record table (exported as "
             "`hff_v2_5_all_records.csv`) but not in the analysis dataset. All describe the superseded "
             "September (v41) labels and exist for v1 rows only.")
    L.append("")
    L.append("| column | type | % present all / included | distinct | description |")
    L.append("|---|---|---:|---:|---|")
    for c in rec_only:
        x = rcov.loc[c]
        L.append(f"| `{c}` | {x['type']} | {x['pct_present_all']:.1f} / {x['pct_present_included']:.1f} "
                 f"| {x['n_distinct']:,} | {DESC_RECORDS_ONLY[c]} |")
    L.append("")
    L += companion_section(a, inc)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT} ({a.shape[1]} analysis columns + {len(rec_only)} record-table-only columns, "
          f"all described)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
