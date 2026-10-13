# HFF evidence map: open data gaps after the v2.2 update

> **Superseded (13 October 2026):** the map is now built from v2.4.1; see
> [DATA_GAPS_v2_4.md](DATA_GAPS_v2_4.md). This file is kept as the record of the v2.2 build.

The map was rebuilt from the HFF dataset v2.2.1 in October 2026: v2.2 (53,782 included studies)
with three studies published before 2010 excluded (item 5), so **53,779 included studies**.
Most figures now use v2.2. The items below are still open, except item 5, which records a decision.
Each one says what is missing or what was decided, what it affects on the site, and how to close it.

## 1. Bibliographic metadata for the studies added after v1 (biggest gap)

**Missing:** `research_funder`, `author_affiliation_countries`, `authors`, `journal`, `doi`,
`url`, `is_oa`, `mesh_theme`, `mesh_source`, `ml_thematic_cluster`, `ml_topics`,
`topic_cluster_id`, `topic_cluster_label`, `topic_cluster_n`.

**For which studies:** the 20,795 studies that entered v2.2 after the September (v1) set:

| route (`origin`) | studies | metadata available anywhere locally? |
|---|---:|---|
| `unsure_original_screening` | 12,670 | no |
| `v11.2_rescreen` | 6,205 | no |
| `pass2_unsure` | 1,130 | yes, in `hff_pipeline_full_single_model_final_v2.csv` (except `is_oa`) |
| `dropped_before_pass2` | 790 | yes, same file (except `is_oa`) |

The v2.2 README lists this as an open item ("Metadata enrichment for the October additions").
Even within v1, funders are reported for only about 20% of studies (CrossRef).

**Effect on the site:** these figures are still built from the HSF extraction 29 Sept v5
(36,495 studies), and each caption says so:

- Topic clusters (all five figures)
- Disease focus (all six figures; MeSH-based)
- Research ownership & collaboration (all six figures)
- Research funding: funder types, top funders, the two funder heatmaps, funder trends, funder to
  authorship flow (the funding priority scorecard is rebuilt from v2.2; it uses no funder data)
- Open access & author countries (all four figures)
- Geographic inequalities: the adjusted odds-ratio forest plot (one panel is "has a local author")
- Overview: the "Who funds the evidence?" card and the open-access part of the
  "Publication access" card. The "DOI or URL available" figure on that card is v2.2 (50%), low
  because the October additions have no DOI yet.

**To close it:** run the same CrossRef / OpenAlex / PubMed enrichment used for v1 on the 18,875
studies with no metadata (plus `is_oa` for the 1,920 gap-route studies), and assign the new
studies to the existing topic clusters. Then drop the figures from `KEEP_V5` in
`docs/dex_hff/keep_v5_metadata_figures_v2_2.py` and rerun the build (below). Agree the method
with the dataset owners first, so the enrichment is done once and the same way.

## 2. Disease burden (DALYs) for Kosovo

The 30 other added countries now have verified IHME GBD 2023 all-cause DALY totals
for 2023, all ages and both sexes, imported from the user-supplied
`IHME-GBD_2023_DATA-e843da6d-1.zip` on 12 October 2026. The export matches existing
country totals to numerical precision. Source rows and the citation are retained locally
in `docs/dex_hff/v2_2/dalys_2023_country_additions_source.csv` and
`dalys_2023_citation.txt`. These countries now participate in the per-DALY outputs.

**Remaining:** Kosovo has no location in this 204-country IHME export. It remains blank
and excluded from per-DALY comparisons. A separately sourced, methodologically comparable
estimate is needed to close this gap.

## 3. Health spending for 5 added countries

No World Bank value for Taiwan, Puerto Rico, Kosovo, Bermuda or Greenland, so they are not in
the per-dollar figures. A source consistent with the other countries is needed (for Taiwan, the
national health accounts are the likely option).

## 4. Smaller items

- **Mauritius and Eritrea have no region** in the country list (an older gap). Both are UN M49
  Sub-Saharan Africa; they are missing from region filters and region figures until set.
- **Geography left unmatched on purpose:** "Congo" (2 studies; could be either Congo), "Northern
  Cyprus" (2; in no reference dataset), and region labels such as "Global", "Multiple", "Europe"
  or "Sub-Saharan Africa", which are counted as region/global scope, not as countries.

## 5. Decision: three studies excluded as published before 2010

The map's publication-year criterion is studies published from 2010 onwards. Three included
studies did not meet it:

| record | title | publication |
|---|---|---|
| 132855712 | Incentives in Obesity and Health Insurance | *Inquiry* 46(4), December 2009 |
| 132855713 | Medicare Savings Programs: Analyzing Options for Expanding Eligibility | *Inquiry* 46(4), December 2009 |
| 132855714 | Medicare Fees and the Volume of Physicians' Services | *Inquiry* 46(4), December 2009 |

**Why they were included:** the search results were brought in through EPPI-Reviewer with no
publication year for these three records, so the year criterion could not be applied. They went
through screening and labelling like every other record and were included in v2.2.

**Why they are excluded now:** an online check (CrossRef and OpenAlex, 12 October 2026) found no
version published in 2010 or later. All three are articles in the "Winter 2009/2010" issue of
*Inquiry*, which both databases date December 2009; the first also exists as an NBER working
paper from May 2007. Their latest publication year is therefore 2009, so they are excluded from
the analysis population under the 2010-onwards criterion. (Their DOIs were registered only in
August 2011, which is a registration date, not a publication date, and may be why the year was
missing.)

**Where this is applied:** in a new dataset version, **v2.2.1**, made by
`docs/dex_hff/make_v2_2_1.py` (the v2.2 files are unchanged). In v2.2.1 the three records have
`analysis_include = False` and `exclusion_reason_v2 = published_before_2010`, the selection flow
(`PRISMA_v2_2_1.json`) has a matching exclusion line, and **53,779 studies are included**; the
change is described in `docs/dex_hff/v2_2/CHANGES_v2_2_1.md`. The site is built from v2.2.1, and
its Methods funnel lists the three among the exclusions. `make_v2_2_csv.py` stops the build if
any study falls outside 2010-2026.

**For the dataset owners:** please take v2.2.1 (or the same change) into the master dataset, so
the dataset's headline count and the map agree at 53,779.

## 6. Income groups: publication year for study counts, current for country comparisons

Income groups follow the World Bank classification. **Analyses that count studies use each study
country's group in the study's publication year (or the current group where that is not
recorded); comparisons between countries use the current (FY2027) classification.** Some
countries changed group during 2010-2026 (56 of the countries in the map; about 5% of
single-country studies would be grouped differently).

- **Publication year:** the Explorer's income filter and income breakdowns; "Study-country pairs
  by income group"; "L&MICs research share over time"; the three Fragile & conflict-affected
  settings figures (which also use each year's FCAS list).
- **Current (FY2027):** country profiles and peer comparisons, maps and country tables, and the
  country-level figures (research vs. burden, the scorecards, research vs. spending, aid vs.
  evidence by region), where each country appears once.
- **Source:** v2.2's `income_level_bundled`, stored per study-country pair as `i` in
  `docs/data/geo.json` by `build_data_v2_2.py` (42,759 of 48,002 pairs). That field lists the
  distinct groups of the countries a study names, not one per country, and v2.2's lookup stops
  at 2025. Where it is empty or lists several groups, the World Bank's historical classification
  fills the gap (`docs/dex_hff/OGHIST_wb_income_history.xlsx`, downloaded 13 October 2026 from
  datacatalogfiles.worldbank.org; 2,384 pairs). The convention is the classification published in
  July of the publication year (fiscal year Y+1), which matches v2.2 for 97.9% of single-country
  studies. The file runs to FY2025, so 2025-26 publications without a v2.2 value use the current
  (FY2027) group (2,858 pairs; for 2026 that is the publication-year group).
- **FCAS figures:** the FCAS share keeps v2.2's own lookup as its base (FCAS status comes from
  it); the comparison by income setting fills studies without a v2.2 group from `geo.json`.
- **Still open:** the figures kept at v5 (forest plot, topic map by income, disease transition,
  disease atlas) use v5's grouping until they are rebuilt from v2.2 metadata (item 1).

## How to rebuild

From `docs/`, after changing any input:

```bash
python dex_hff/make_v2_2_1.py                    # v2.2 -> v2.2.1 (excludes the three pre-2010 studies)
python dex_hff/make_v2_2_csv.py                  # v2.2.1 analysis file -> site layout
python dex_hff/build_data_v2_2.py                # data/*.json, Overview tiles, Methods funnel
python dex_hff/build_study_meta_v2_2.py          # Explorer CSV download
python dex_hff/build_texts_v2_2.py               # Country profile titles and abstracts (splits files over ~20 MB; see README)
python dex_hff/build_glance_regions_v2_2.py      # "(Un)equal weight at a glance" page
python dex_hff/build_figures_v2_2.py             # gallery figures (about 15 minutes)
python dex_hff/build_fcas_outcomes_v2_2.py       # FCAS and outcome figures
python dex_hff/keep_v5_metadata_figures_v2_2.py  # keeps the metadata figures at v5 (item 1)
```

To change only a few figures, use quick mode (about 2 minutes instead of 15). It writes only the
named images and updates only their gallery entries in `content.json`:

```bash
python dex_hff/build_figures_v2_2.py --only fig_income_bar.png,fig_equity_time.png
```

Quick mode is for figures made by `build_figures_v2_2.py`, not for the figures kept at v5 (item 1).
After `build_data_v2_2.py` changes data that many figures use, run the full build instead.

`make_country_additions_v2_2.py` fetches population and spending online and only needs rerunning
if the country list changes. The raw v2.2 files live in `docs/dex_hff/v2_2/`, which is
git-ignored: the dataset is internal and must not be published.
