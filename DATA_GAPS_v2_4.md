# HFF evidence map: data notes and open gaps after the v2.4 update

The map is built from the HFF dataset **v2.4.1** (October 2026): the dataset team's v2.4 (53,365
included studies) with three studies published before 2010 excluded (item 5), so **53,362
included studies**. The earlier notes for the v2.2 build are in `DATA_GAPS_v2_2.md` (history).

v2.4 differs from v2.2 in two ways, both from the dataset team:

- **v2.3: bibliographic metadata for every study.** The 20,375 studies added after the September
  (v1) set now have DOI, authors, affiliation countries, funders, journal, open access, language
  and MeSH/OpenAlex topics, from one CrossRef search per record plus an OpenAlex DOI lookup. The
  topic clusters were refitted for every study (56 clusters plus "unclustered"; the old values
  are kept in `topic_cluster_*_v2`).
- **v2.4: 417 duplicate studies removed by DOI** (Decision 16, L. Sempe, 13 October 2026), found
  once every route had DOIs. Every case and ruling is in `dedupe_doi_review_v2_4.csv`.

A record-by-record check (13 October 2026) against our cleaned v2.2.1 found: no analysis field
changed for any of the 53,362 studies the two versions share (title, abstract, year, functions,
outcomes, design, data, geography, income); bibliographic fields were only filled where empty,
never overwritten; the only studies dropped are the 417 `duplicate_doi`; and v2.4 includes again
the three pre-2010 studies, because it was built from v2.2, not v2.2.1.

## 1. Topic map coordinates (the only figures still on v5)

**Missing:** the 2-D map positions (x, y) of the refitted v2.4 topic model.

**Effect on the site:** "A handful of themes dominate the thematic landscape" (`fig_topicmap.png`)
and the topic map by income (`fig_topicmap_income.png`) plot each study at its position in the
old topic model (`docs/dex_hff/topic_map.csv`, v1 studies only, old cluster numbers). They stay as
built from the HSF extraction 29 Sept v5 (36,495 studies), and their captions say so. Every other
figure is built from v2.4.1, including the "Top 20 research themes" ranking from the new clusters.

**To close it:** ask the dataset team for the v2.4 model's per-study coordinates (`record_id, x, y,
cluster`), replace `topic_map.csv` with them, drop `keep_v5_topicmap_figures_v2_4.py` from the
build, and rerun the build.

**Note on metadata coverage:** it differs by route (DOI for 57% to 90% of studies); funders are
reported for about 18% of studies overall, so the funding figures describe studies that report a
funder. Figure footnotes state their bases.

## 2. Disease burden (DALYs) for Kosovo

The 30 other added countries have IHME GBD 2023 all-cause DALY totals (2023, all ages, both sexes),
imported from `IHME-GBD_2023_DATA-e843da6d-1.zip` on 12 October 2026 (source rows and citation in
`docs/dex_hff/v2_2/dalys_2023_country_additions_source.csv` and `dalys_2023_citation.txt`).
Kosovo is not a GBD location, so it stays out of the per-DALY comparisons until a comparable
estimate is found.

## 3. Health spending for 5 added countries

No World Bank value for Taiwan, Puerto Rico, Kosovo, Bermuda or Greenland, so they are not in the
per-dollar figures. A source consistent with the other countries is needed (for Taiwan, the
national health accounts are the likely option).

## 4. Smaller items

- **Mauritius and Eritrea have no region** in the country list (an older gap). Both are UN M49
  Sub-Saharan Africa; they are missing from region filters and region figures until set.
- **Geography left unmatched on purpose:** "Congo" (2 studies; could be either Congo), "Northern
  Cyprus" (2; in no reference dataset), and region labels such as "Global", "Multiple", "Europe"
  or "Sub-Saharan Africa", which are counted as region/global scope, not as countries.
- **Taiwan** follows the World Bank ("Taiwan, China"): a separate entry from China, high income in
  every year, East Asia & Pacific wherever World Bank regions are used. The site shows it as
  "Taiwan".

## 5. Decision: three studies excluded as published before 2010

The map includes studies published from 2010 onwards. Three included studies did not meet it:

| record | title | publication |
|---|---|---|
| 132855712 | Incentives in Obesity and Health Insurance | *Inquiry* 46(4), December 2009 |
| 132855713 | Medicare Savings Programs: Analyzing Options for Expanding Eligibility | *Inquiry* 46(4), December 2009 |
| 132855714 | Medicare Fees and the Volume of Physicians' Services | *Inquiry* 46(4), December 2009 |

**Why they were included:** the search results were brought in through EPPI-Reviewer with no
publication year for these three records, so the year criterion could not be applied. They went
through screening and labelling like every other record.

**Why they are excluded:** an online check (CrossRef and OpenAlex, 12 October 2026) found no
version published in 2010 or later. All three are articles in the "Winter 2009/2010" issue of
*Inquiry*, which both databases date December 2009; the first is also an NBER working paper from
May 2007. (Their DOIs were registered only in August 2011, which may be why the year was missing.)

**Where this is applied:** `docs/dex_hff/make_v2_4_1.py` makes **v2.4.1** from v2.4 (whose files
are unchanged): the three records get `analysis_include = False` and `exclusion_reason_v2 =
published_before_2010`, and `PRISMA_v2_4_1.json` has a matching exclusion line; see
`docs/dex_hff/v2_4_1/CHANGES_v2_4_1.md`. (v2.2.1 had made the same change to v2.2.) The site's
Methods funnel lists them among the exclusions; `make_v2_4_csv.py` stops the build if any study
falls outside 2010-2026.

**For the dataset owners:** v2.4 includes these three again. Please apply the same exclusion in the
master dataset, so its headline count and the map agree at 53,362.

## 6. Income groups: publication year for study counts, current for country comparisons

Income groups follow the World Bank classification. **Analyses that count studies use each study
country's group in the study's publication year (or the current group where that is not
recorded); comparisons between countries use the current (FY2027) classification.** Some
countries changed group during 2010-2026 (about 5% of single-country studies would be grouped
differently).

- **Publication year:** the Explorer's income filter and income breakdowns; "Study-country pairs
  by income group"; "L&MICs research share over time"; the three Fragile & conflict-affected
  settings figures (which also use each year's FCAS list).
- **Current (FY2027):** country profiles and peer comparisons, maps and country tables, and the
  country-level figures (research vs. burden, the scorecards, research vs. spending, aid vs.
  evidence by region), where each country appears once.
- **Source:** the dataset's `income_level_bundled`, stored per study-country pair as `i` in
  `docs/data/geo.json` by `build_data_v2_4.py` (42,425 of 47,650 pairs). That field lists the
  distinct groups of the countries a study names, not one per country, and its lookup stops at
  2025. Where it is empty or lists several groups, the World Bank's historical classification
  fills the gap (`docs/dex_hff/OGHIST_wb_income_history.xlsx`, downloaded 13 October 2026; 2,371
  pairs), using the classification published in July of the publication year (fiscal year Y+1),
  which matches the dataset for 97.9% of single-country studies. The file runs to FY2025, so
  2025-26 publications without a dataset value use the current (FY2027) group (2,854 pairs; for
  2026 that is the publication-year group).
- **FCAS figures:** the FCAS share keeps the dataset's own lookup as its base (FCAS status comes
  from it); the comparison by income setting fills studies without a dataset group from `geo.json`.

## How to rebuild

From `docs/`, after changing any input:

```bash
python dex_hff/make_v2_4_1.py                    # v2.4 -> v2.4.1 (excludes the three pre-2010 studies)
python dex_hff/make_v2_4_csv.py                  # v2.4.1 analysis file -> site layout
python dex_hff/build_data_v2_4.py                # data/*.json, Overview tiles, Methods funnel
python dex_hff/build_study_meta_v2_4.py          # Explorer CSV download
python dex_hff/build_texts_v2_4.py               # Country profile titles and abstracts (splits files over ~20 MB; see README)
python dex_hff/build_glance_regions_v2_4.py      # "(Un)equal weight at a glance" page
python dex_hff/build_figures_v2_4.py             # gallery figures (about 15 minutes)
python dex_hff/build_funder_types_v2_4.py        # funder-type figure and the Overview funder card
python dex_hff/build_fcas_outcomes_v2_4.py       # FCAS and outcome figures
PYTHONIOENCODING=utf-8 python dex_hff/build_open_access_v2_4.py   # open-access figures and Overview card
python dex_hff/keep_v5_topicmap_figures_v2_4.py  # keeps the two topic maps at v5 (item 1)
```

To change only a few figures, use quick mode (about 2 minutes instead of 15). It writes only the
named images and updates only their gallery entries in `content.json`:

```bash
python dex_hff/build_figures_v2_4.py --only fig_income_bar.png,fig_equity_time.png
```

Quick mode is for figures made by `build_figures_v2_4.py`, not for the two topic maps kept at v5.
After `build_data_v2_4.py` changes data that many figures use, run the full build instead.

On Windows, run `build_open_access_v2_4.py` with `PYTHONIOENCODING=utf-8` (or in a UTF-8
terminal): it prints captions containing "≥", which the default console encoding cannot show.

The v2.4 files from the dataset team are in `docs/dex_hff/v2_4-2_2metadata update/hff_share_v2_4/`
and v2.4.1 in `docs/dex_hff/v2_4_1/`; both are git-ignored: the dataset is internal and must not
be published. `make_country_additions_v2_2.py` fetches population and spending online and only
needs rerunning if the country list changes.
