# Build scripts

The Python scripts that build the HFF evidence map's data and figures from the HFF dataset
v2.5.1 (53,411 included studies). The site itself (`docs/`) is static: these scripts write the
JSON files in `docs/data/` and the images in `docs/figures/`, which are committed and published.

**The raw inputs are not in this repository.** The scripts read them from `docs/dex_hff/`,
which is kept locally (dataset CSVs, IHME and World Bank workbooks). To run the scripts, ask for
a copy of that folder and put it at `docs/dex_hff/`.

Requirements: Python 3.12 with `pandas`, `numpy`, `matplotlib` and `openpyxl`; `build_figures_v2_5.py`
also needs `plotly` and `kaleido` for the bivariate map. Run every script
from the repository root, with `PYTHONIOENCODING=utf-8` set.

## Run order

```bash
export PYTHONIOENCODING=utf-8
# 1. Dataset -> site layout
python scripts/make_v2_5_1.py                       # v2.5 -> v2.5.1 (drops three pre-2010 studies)
python scripts/make_v2_5_csv.py                     # v2.5.1 -> docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv
# 2. Site data (docs/data/)
python scripts/build_data_v2_5.py                   # studies, countries, codebook, Overview tiles
python scripts/build_study_meta_v2_5.py             # titles/authors/DOIs for the Explorer CSV download
python scripts/build_study_filters_v2_5.py          # Explorer funder and language filters
python scripts/build_texts_v2_5.py                  # per-country titles and abstracts
python scripts/build_study_text.py                  # every study's title and abstract for the CSV download
# 3. Figures (docs/figures/)
python scripts/build_glance_regions_v2_5.py         # "(Un)equal weight at a glance" page
python scripts/build_figures_v2_5.py                # gallery figures (about 5 minutes)
python scripts/build_funder_types_v2_5.py
python scripts/build_fcas_outcomes_v2_5.py
python scripts/build_open_access_v2_5.py
python scripts/build_outcome_combined_v2_5.py       # after build_figures and build_fcas_outcomes
python scripts/build_function_outcome_themes_v2_5.py
# 4. Approved plain-language copy on the gallery figures
python scripts/copy/render_copy_v2_5.py v2_5 rendered_v2_5
```

A full run does not reproduce the published site by itself: some text was edited by hand after
the build (plain-language copy, `docs/data/content.json`, the glance page). See
[DATA_GAPS_v2_5.md](../DATA_GAPS_v2_5.md#how-to-rebuild) before re-running anything that writes
to `docs/`.

## What each script does

| Script | Writes |
|---|---|
| `make_v2_5_1.py`, `make_v2_5_csv.py` | the site-layout dataset in `docs/dex_hff/v2_5_1/` |
| `build_data_v2_5.py` | `docs/data/` core JSON (`studies`, `geo`, `countries`, `dict`, `function`, `outcome`, `content`) |
| `build_study_meta_v2_5.py` | `docs/data/study_meta.json` |
| `build_study_filters_v2_5.py` | `docs/data/study_filters.json` |
| `build_texts_v2_5.py` | `docs/data/texts/<ISO3>.json` |
| `build_study_text.py` | `docs/data/text/` (`index.json` and chunks `000.json`... of 2,000 studies): titles and abstracts of every study, as in the analysis master, for the Explorer CSV download. Rerun when the master or `studies.json` changes |
| `build_figures_v2_5.py` | most gallery figures (`--only fig_a.png,fig_b.png` rebuilds just those) |
| `build_funder_types_v2_5.py`, `build_open_access_v2_5.py`, `build_fcas_outcomes_v2_5.py`, `build_outcome_combined_v2_5.py`, `build_function_outcome_themes_v2_5.py` | one figure family each, plus their summary JSON |
| `build_glance_regions_v2_5.py`, `build_glance_regions_functions_v2_5.py`, `build_glance_at_a_glance_v2_5.py`, `build_glance_manuscript_v2_5.py` | the "at a glance" HTML pages (site, functions, manuscript variants) |
| `build_hidden_figures_v5.py` | figures kept in the repo but hidden on the site |
| `build_descriptive_summary_v2_5.py` | a standalone four-panel summary figure (not on the site) |
| `make_country_regions_v2_4.py` | `docs/dex_hff/country_regions_v2_4.csv` (WHO/UN/World Bank regions; fetches online) |
| `search_urls_hta_v2_5_1.py` | publication links for the HTA studies with no DOI (queries OpenAlex) |
| `fig_text_fit.py` | helper imported by the figure scripts; keeps notes inside each image |
| `copy/render_copy_v2_5.py` | re-renders gallery figures with the approved copy in `copy/figure_copy_v2_5.json` |
| `dataset/` | the dataset team's scripts that produce HFF v2.5 itself (they run in that team's repository, not here) |

The `_v2_4` / `_v2_2` / `_v5` names in a few current files are historical: those scripts were
carried forward unchanged. Earlier versions of every script are in [archive/scripts_old](../archive/scripts_old/).
