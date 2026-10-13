# HFF evidence map: data notes after the v2.5 update

The map is built from the HFF dataset **v2.5.1** (13 October 2026): the dataset team's v2.5 (53,414
included studies) with the three studies published before 2010 excluded again (item 5), so
**53,411 included studies**. Everything not listed here is as in
[DATA_GAPS_v2_4.md](DATA_GAPS_v2_4.md), which stays the reference for the open gaps (DALYs for
Kosovo, health spending for added countries, income groups, regions).

## What v2.5 changes

v2.5 is v2.4 with two changes from the dataset team (`V2_5_DATASET_README.md`):

- **Decision 17: a record that describes itself as a health technology assessment (HTA) is
  Benefits decisions.** 49 HTAs excluded in v2.4 for having no financing function are included
  again (`function_label_source = hta_rule_decision17`), and 139 included studies gain Benefits
  decisions as their first (primary) function. The pre-rule label is kept in
  `financing_function_v52_pre_hta`.
- **`also_in_hee` flags the 1,874 studies also included in the HEE arm.** The site does not use
  this flag yet. If the overlap is reported, report each arm on its own count and never add them.

No other field changed for the studies v2.4 and v2.5 share. On the site:

| | v2.4.1 | v2.5.1 |
|---|---:|---:|
| Included studies | 53,362 | **53,411** |
| Studies with Benefits decisions | 13,088 | **13,276** |
| Excluded: no financing function (Methods funnel) | 10,982 | **10,933** |
| Disease-classified studies (PubMed MeSH) | 7,874 | **7,881** |

The other function counts are unchanged. Primary-function figures (the alluvial charts) move
studies to Benefits decisions, mostly from public financial management.

## 1. Topic maps: the 49 HTA studies are not shown

The 49 re-included HTA studies are not in the topic model (it was fitted on the v2.3 included set),
so they have no topic cluster or map position. The two topic maps and the topic rankings still
cover the 53,362 studies with a topic embedding; the topic map's technical note says so.
**To close it:** ask the dataset team to project the 49 into the v2.4 model.

## 2. Second-opinion sensitivity figure

`fig_function_second_opinion_v2_2.png` compares function shares with and without the
second-opinion labels. The 49 HTA studies are labelled by the Decision 17 rule, not the main panel,
but the figure counts them on the panel side. The effect is under 0.1% of studies.

## 3. Publication links from EPPI-Reviewer for studies without a DOI

The dataset's `url` column holds only doi.org links, so 11,239 studies had no DOI and no link.
Links now come from EPPI-Reviewer RIS exports, matched on U1 = record_id. They are stored as
lookup files in `docs/dex_hff/v2_5_1/eppi_urls/`, and `make_v2_5_csv.py` fills only studies with no
DOI and no URL:

- `eppi_ris_v2_4_1_matches.csv`: 9,329 studies matched for v2.4.1 (`v2_4_1/url_search/eppi_ris/`,
  `retrieve_eppi_urls.py`; record_id match, exact normalized title, year within one).
- `eppi_ris_hta_28.csv`: the 28 Decision 17 HTA studies without a DOI (export of 13 October 2026).

For each study the link is chosen in this order:

1. the RIS DOI as a doi.org link (4,643 studies);
2. else, for Ovid MEDLINE records, the public PubMed page for the accession number, which is the
   PubMed ID (767; the Ovid link needs a subscription);
3. else the RIS link as exported: Scopus record (2,720), other publisher or agency pages (709),
   PDFs (432), Cochrane CENTRAL (86).

The Scopus and Cochrane CENTRAL records may need a subscription to open. The links were not checked
online.

Studies with a publication link: 42,144 → **51,501 (96.4%)**; 1,910 still have none. The `doi` column,
the DOI count and the open-access figures are unchanged, because the RIS DOIs were only used as links.

## 5. Decision: three studies excluded as published before 2010

v2.5, like v2.4, includes the three December 2009 *Inquiry* articles again (records 132855712-14,
no publication year at import). `docs/dex_hff/make_v2_5_1.py` excludes them as
`published_before_2010`, exactly as `make_v2_4_1.py` did; see
`docs/dex_hff/v2_5_1/CHANGES_v2_5_1.md` and item 5 of DATA_GAPS_v2_4.md for the evidence.
**For the dataset owners:** please apply this exclusion in the master dataset, so its headline
count and the map agree at 53,411.

## How to rebuild

From `docs/` (the `_v2_5` scripts are copies of the `_v2_4` ones that read
`dex_hff/v2_5_1/hff_v2_5_1_site.csv`; the `_v2_4` scripts are unchanged):

```bash
python dex_hff/make_v2_5_1.py                    # v2.5 -> v2.5.1 (excludes the three pre-2010 studies)
python dex_hff/make_v2_5_csv.py                  # v2.5.1 analysis file -> site layout
export PYTHONIOENCODING=utf-8
python dex_hff/build_data_v2_5.py                # data/*.json, Overview tiles, Methods funnel
python dex_hff/build_study_meta_v2_5.py          # Explorer CSV download
python dex_hff/build_texts_v2_5.py               # Country profile titles and abstracts
python dex_hff/build_glance_regions_v2_5.py      # "(Un)equal weight at a glance" page
python dex_hff/build_figures_v2_5.py             # gallery figures (about 5 minutes)
python dex_hff/build_funder_types_v2_5.py
python dex_hff/build_fcas_outcomes_v2_5.py
python dex_hff/build_open_access_v2_5.py
python dex_hff/build_outcome_combined_v2_5.py    # after build_figures and build_fcas_outcomes
python dex_hff/build_function_outcome_themes_v2_5.py
```

**These scripts do not produce the published site on their own.** After them, three things must
be re-applied:

- **Plain-language figures.** 70 gallery figures carry the approved plain-language titles and
  captions. Re-render them with
  `python dex_hff/plain_language_review/render_copy_v2_5.py v2_5 rendered_v2_5`, then copy the
  PNGs into `figures/`. The renderer reads `figure_copy_v2_5.json`, the approved copy with its
  counts updated to v2.5.1 (disease 7,881 of 53,411; "Other" without a theme 6,830; Benefits
  decisions share 25% at the end of the period; 536 studies in the funder flow).
- **Edited text in `data/content.json`.** The approved wording, technical notes and Kosovo notes
  were written into this file by hand, and a full build overwrites them.
- **Edited text in `figures/fig_glance_regions.html`.** The title and footer were also edited by
  hand.

For the v2.5 update, the content.json and glance-page edits were carried over with a three-way
merge. The baseline was a fresh v2.4.1 build, the committed files held the edits, and the v2.5.1
build gave the new numbers. Edited text was kept. Technical notes copied from v2.4.1 figure text
were replaced with the v2.5.1 text. Two notes were updated by hand: function bar 13,276; combined
scorecard Eritrea 5,238.

The v2.5 files from the dataset team are in `docs/dex_hff/v2.5 from Lucas/hff_share_v2_5/` and
v2.5.1 in `docs/dex_hff/v2_5_1/`. Both are git-ignored: the dataset is internal and must not be
published.
