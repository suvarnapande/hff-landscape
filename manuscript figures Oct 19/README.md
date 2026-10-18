# Manuscript figures (19 October 2026)

Figures for the journal manuscript, in the house print style set by `theme_hee.R`
(a copy of `docs/theme_hee.R`, kept here so the folder is self-contained).

| Figure | File | Status |
|---|---|---|
| 1. Health financing studies per 10 million people, by country studied | `fig1_studies_per_10m_map.png` / `.pdf` | Redrawn in R with `theme_hee.R`: one-hue blue scale (`hee_ord`) instead of the earlier red–yellow–blue |
| 2–7. Functions by income group and by WHO region; topics per function; outcomes examined; outcomes within each function; author location by income group | `figs 2-7 screenshots/` | Already in `theme_hee` style; the files here are screen captures of the existing figures, not full-resolution originals |
| 8. How regional shares of health aid and research compare | `fig8_aid_vs_research_region.png` / `.pdf` | Redrawn in R with `theme_hee.R` (was in the website's style) |

Figures 1 and 8 use the site data (HFF dataset v2.5.1): 47,693 study-country pairs across
184 countries. The earlier map reported 47,488 pairs across 198 countries and territories,
so it was built from a different data version.

## Rebuilding figures 1 and 8

From this folder:

```
python prep_data.py      # writes map_per10m.csv and aid_vs_research.csv from docs/data
Rscript make_figures.R   # draws both figures as 300 dpi PNG and vector PDF, 183 mm wide
```

R packages: ggplot2, scales, ggtext, sf, rnaturalearth, rnaturalearthdata, ragg.
`make_figures.R` also looks in `./_rlib` (not committed) for packages installed locally.
