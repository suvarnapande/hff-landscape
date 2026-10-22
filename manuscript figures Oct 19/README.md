# Manuscript figures (19 October 2026)

Figures for the journal manuscript, in the house print style set by `theme_hee.R`
(a copy of `docs/theme_hee.R`, kept here so the folder is self-contained).

| Figure | File | Status |
|---|---|---|
| 1. Health financing studies per 10 million people, by country studied | `fig1_studies_per_10m_map.png` / `.pdf` | Redrawn in R with `theme_hee.R`: one-hue blue scale (`hee_ord`) instead of the earlier red–yellow–blue |
| 2–7. Functions by income group and by WHO region; topics per function; outcomes examined; outcomes within each function; author location by income group | `figs 2-7 screenshots/` | Already in `theme_hee` style; the files here are screen captures of the existing figures, not full-resolution originals |
| 8. How regional shares of health aid and research compare | `fig8_aid_vs_research_region.png` / `.pdf` | Redrawn in R with `theme_hee.R` (was in the website's style) |
| (Un)equal weight, map only: financing function studied most often, by country | `fig_unequal_weight_leading_function_map.png` / `.pdf` | New: static version of the site's interactive page. Maps may use only three colours (`hee_cat3`), so the three functions leading the most countries are coloured and the other four share one grey |
| (Un)equal weight, full figure: A the map, B function mix by WHO region, C financial protection as an outcome, D country coverage over time | `fig_unequal_weight_full.png` / `.pdf` | New: full-page (183 x 269 mm) static version of the whole interactive page. Panel B shows the same breakdown as figure 3 |

| The evidence at a glance: headline numbers, country coverage note, A: leading financing function by country | `fig_glance_1_evidence_at_a_glance.png` / `.pdf` | New, laid out like the HEE "evidence at a glance" reference; supersedes the (Un)equal weight figures above |
| Profile of studies by WHO region: headline numbers, then per region the function mix (dots, map colours), top three functions, financial protection bar and coverage trend | `fig_glance_2_profile_by_region.png` / `.pdf` | New, laid out like the HEE "profile of studies by WHO region" reference |

| **Current, aligned with HSF_Interim_Manuscript_Draft_v2.0.docx:** the evidence at a glance (manuscript headline numbers; studies per 10 million people; n = 47,488 pairs) and the profile by WHO region (manuscript Figure 4 function shares, single-country studies; financial protection among single-country studies with a classifiable outcome) | `fig_glance_1_evidence_at_a_glance_v5.png`, `fig_glance_2_profile_by_region_v4.png` (+ `.pdf`) | Drawn by `make_glance_figures_v3.R`; earlier `_v2`-`_v4` versions are kept for reference. Figure 1's per-10-million map with the manuscript's caption totals is `fig1_studies_per_10m_map_v2` |

Figures 1, 8, the (Un)equal weight and the glance figures use the site data (HFF dataset v2.5.1): 47,693 study-country pairs across
184 countries. The earlier map reported 47,488 pairs across 198 countries and territories,
so it was built from a different data version.

## Rebuilding the redrawn figures

From this folder:

```
python prep_data.py      # writes the CSVs (map, aid vs research, leading function, region profiles) from docs/data
Rscript make_figures.R   # draws all four figures as 300 dpi PNG and vector PDF, 183 mm wide
Rscript make_glance_figures.R   # draws the two "evidence at a glance" figures (also uses kpis.csv)
```

## Auditing the numbers

Both audits recompute from the raw dataset (`docs/dex_hff/v2_5_1/hff_v2_5_1_site.csv`), not from the
site's processed JSON or the CSVs above, so they check both pipelines independently:

```
python audit_manuscript_text.py   # numbers quoted in the manuscript text -> audit_manuscript_text_report.md
python audit_figures.py           # figure input CSVs and numbers typed into the R scripts -> audit_figures_report.md
```

Each row is PASS, DIFF or INFO (no number to compare). `audit_common.py` holds the shared loader.

R packages: ggplot2, scales, ggtext, sf, rnaturalearth, rnaturalearthdata, ragg.
`make_figures.R` also looks in `./_rlib` (not committed) for packages installed locally.

## Income and region basis (22 October 2026)

Studies are now counted by the World Bank income group of each country studied **in the study's
publication year** (site data `docs/data/geo.json` "i"), not the current FY2027 group. New files
(earlier versions and outputs are kept):

| Script | Writes |
|---|---|
| `prep_data_v2.py` | `kpis_v2.csv` (L&MIC share 36.7%, was 35.4%), `aid_vs_research_v2.csv` (Mauritius and Eritrea now in Sub-Saharan Africa), `oa_by_income_v2.csv`, `fig2_functions_by_income_v2.csv`, `fig7_author_location_by_income_v2.csv` |
| `make_open_access_figure_v2.R` | `fig_open_access_by_income_v2` |
| `make_income_figures_v2.R` | `fig2_functions_by_income_v2`, `fig7_author_location_by_income_v2` (redrawn; the screenshots used the current group) |
| `make_figures_v2.R` | `fig8_aid_vs_research_region_v2` (caption: current FY2027 group for the GBD approximation), `fig_unequal_weight_full_v2` (region caption) |
| `make_glance_figures_v4.R` | `fig_glance_2_profile_by_region_v5` (caption no longer says "WHO regions as assigned by WHO") |
| `audit_manuscript_text_v2.py` (+ `audit_common_v2.py`) | `audit_manuscript_text_report_v2.md`: each DIFF is a manuscript number to update |

Regions: the six WHO regions; Taiwan and Hong Kong (Western Pacific) and Kosovo (European), which WHO
does not assign, take the WHO region of their UN M49 sub-region. Run order: `prep_data.py`,
`prep_data_v2.py`, then the R scripts. Rerun all of them if `docs/data/geo.json` is rebuilt (for
example with a newer World Bank history file).
