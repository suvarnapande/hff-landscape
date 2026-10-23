# Notes for AI assistants and new contributors

Read this before changing anything. It records how this repository works and the decisions
that are not obvious from the code. **Run `git pull` first**, then `git log --oneline -15` to
see what changed recently.

## What this is

The HFF (health financing functions) evidence map: a static site in `docs/` (plain HTML/JS,
no build step), published with GitHub Pages from this public repository. Current data: **HFF
dataset v2.5.1**, 53,411 included studies published 2010–2026.

| Folder | What it holds | In git? |
|---|---|---|
| `docs/` | the website: `index.html`, `app.js`, `styles.css`, `data/*.json`, `figures/` | yes, and published |
| `scripts/` | the Python scripts that build `docs/data` and `docs/figures`; run order in `scripts/README.md` | yes |
| `scripts/dataset/` | the dataset team's scripts that make HFF v2.5 (run in their repository) | yes |
| `manuscript figures Oct 19/` | R scripts and outputs for the interim manuscript, styled with `theme_hee.R` | yes |
| `archive/` | superseded scripts, v4 data and figures, mockups; nothing uses them | yes |
| `docs/dex_hff/` | raw inputs (dataset CSVs, IHME and World Bank workbooks) | **no, local only** |

Background and decisions: `README.md`, `DATA_GAPS_v2_5.md` (current version, rebuild steps),
`DATA_GAPS_v2_4.md` (countries, income groups, regions, open data gaps).

## Rules

- **Don't run the full build to make a small change.** The build overwrites text that was
  edited by hand afterwards: the plain-language wording in `docs/data/content.json`, the glance
  page's title and footer, and 70 gallery figures re-rendered with approved copy. To change one
  figure, run its script with `--only fig_name.png` and keep only that file. For a new dataset
  version, follow "How to rebuild" in `DATA_GAPS_v2_5.md` (three-way merge of the edits).
  *Why: found during the v2.5.1 update (13 October 2026); the edits had to be merged back in.*
- **Never commit raw data** (`docs/dex_hff/`) or the IHME Financing Global Health workbooks
  (`F01`–`F12`). *Why: the repository is public, the raw files run to gigabytes, and IHME's
  terms set conditions on redistribution.*
- **After changing `docs/app.js` or any file in `docs/data/`,** bump `BUILD` at the top of
  `app.js` and the matching `?v=` in `index.html`. *Why: otherwise browsers keep showing
  cached copies of the old files.*
- **Hidden figures stay in git.** Hide a figure or section from the site through
  `HIDDEN_SECTIONS` / `HIDDEN_FIGS` in `docs/app.js`; don't delete the image. *Why: the
  project lead's preference, so hidden figures can be brought back.*
- **Substantial script changes go in a new versioned copy** (e.g. `build_x_v2_6.py`), not an
  in-place edit. *Why: earlier versions stay runnable for comparison, as with `_v2_2`, `_v2_4`
  and `_v2_5`.*
- **Run scripts from the repository root** with `PYTHONIOENCODING=utf-8` and plain `python`.
  *Why: paths are set relative to the root, and the figure scripts import `fig_text_fit` from
  `scripts/`.*
- **After `scripts/copy/render_copy_v2_6.py` (or `_v2_5`), restore `docs/data/funder_types_v5.csv`** with
  `git checkout`. *Why: the renderer rewrites it as a side effect (row order only); noticed when
  re-rendering figures.*
- **Rebuild country text files only with `build_texts_v2_5.py`.** It splits large countries into
  parts (`USA.json` points to `USA.1.json`, `USA.2.json`). *Why: with v2.2 the United States
  file reached about 28 MB, and GitHub Pages rejects files over 25 MiB.*

## Conventions

- **Places:** 185 countries and territories (184 with studies). The list was inherited from the
  HEE dashboard plus 31 additions; it is not the World Bank's list. Say "countries and
  territories" in text.
- **Income groups:** World Bank. Study counts use the group in the publication year; country
  comparisons (maps, profiles) use the current FY2027 group. Author countries (open access,
  co-authorship) also use the publication year (`scripts/wb_income_history.py`). Every figure,
  caption and label says which basis it uses; the renderer keeps only a footnote's first
  sentence, so put the basis there or in the copy's `basis` field.
- **FCAS:** the World Bank list of fragile and conflict-affected situations for the publication
  year; 2026 studies use the latest list available to the dataset.
- **Regions:** the six WHO regions. Taiwan and Hong Kong (Western Pacific) and Kosovo (European)
  are not assigned by WHO and take the region of their UN sub-region. One figure (aid vs.
  evidence) uses approximate IHME GBD super-regions and says so.
- **Wording:** "L&MICs", not "LMICs". Site text is plain language; new filter and figure text
  follows the existing `?` help style in `app.js` (`FILTER_HELP`).
- **Counting:** a study naming several countries, functions, outcomes or funders counts once in
  each, so shares can sum to more than 100%.
- **DALYs are not an HFF focus.** They are leftovers from the HEE dashboard (profile tile, bottom
  chart, landscape bubble chart, Explorer map/scatter options). Don't add DALY wording or
  definitions to captions or notes, and prefer health spending or population as comparisons.
  *Why: the project lead's decision, 23 October 2026.*
- **One chart, one question.** Don't put unrelated measures (e.g. type of analysis, has DOI,
  data source) on one axis; give a separate measure its own chart or a sentence.
- **Country profiles** compare with countries in the same current (FY2027) income group: tiles
  and the bottom chart use the median, studies per year the average per country, and the
  function, design and analysis charts pooled shares. Keep the technical note in
  `index.html` in step if this changes. Everything on the profile shows all studies except
  the study grid, which follows Explorer filters and says so ("Show all" toggle).
- **Checking changes:** there are no automated tests. `node --check docs/app.js` catches syntax
  errors. The data functions exported from `app.js` (`loadData`, `applyFilters`,
  `countryProfile`, `studiesStrip`, ...) run in Node if you set `globalThis.window` and a stub
  `document` before importing, and load the `docs/data/*.json` files with `fs`.

## Recent changes

- 2026-10-23: Explorer CSV download shows a progress bar (files and MB loaded); the
  Explorer "type of analysis" tile shows percentages only (no bar); study lists in country
  profiles link each study's DOI or URL (from `docs/data/study_meta.json`).
- 2026-10-23: country profiles: the "How studies are done and reported" chart (quantitative,
  has DOI, administrative data on one axis) is replaced by a type-of-analysis chart; the DOI
  share is a sentence under it. `signal_metrics` in `content.json` is no longer used.
- 2026-10-23: country profiles: long function and design labels wrap (hover keeps the full
  name); the technical note says which comparison (median, average, pooled shares) each
  part of the page uses.
- 2026-10-23: country profiles: DALY definition and DALY wording removed from the caption and
  technical note (DALYs are not an HFF focus; the tile and bottom chart still use them). The
  study grid says when Explorer filters narrow it, with a "Show all" toggle; study design
  labels back to one line (too many rows to wrap).
- 2026-10-22: income basis made consistent (`build_figures_v2_6.py`, `build_fcas_outcomes_v2_6.py`,
  `build_open_access_v2_6.py`, `copy/render_copy_v2_6.py`): eight figures that counted studies by
  current income now use the publication year; footnotes, Explorer labels, the CSV column and the
  glance L&MICs share (35% -> 37%) state or use the right basis. Manuscript figures: `_v2` copies.
- 2026-10-22: Explorer CSV download takes titles and abstracts (new last column) for every
  study from `docs/data/text/` (`scripts/build_study_text.py`); rerun it when the master or
  `studies.json` changes.
- 2026-10-21: manuscript figures for funder types, open access by income, and section 3.2.1
  size and growth (`manuscript figures Oct 19/`).
- 2026-10-20: scripts moved from `docs/dex_hff/` to `scripts/`, old versions to `archive/`;
  superseded raw datasets zipped locally (`archive/raw_old.zip`, not in git).
- 2026-10-20: Explorer gained **Funder** and **Publication language** filters
  (`docs/data/study_filters.json`, from `scripts/build_study_filters_v2_5.py`). About 18% of
  studies name a funder; publication language is not recorded for about a third.

For anything newer, see `git log`. Add a line here when you make a change others should know about.
