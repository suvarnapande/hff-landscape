# HFF evidence map — interactive

Static site for the health-financing-functions evidence map: pure HTML/JS (no server, no
build step), served from `docs/`. Forked from the `hee-landscape` dashboard scaffold and
rebuilt against the HFF extraction.

Data pipeline: `docs/dex_hff/build_data.py` reads
`docs/dex_hff/hff_pipeline_full_single_model.csv` (52,826 LLM-classified records) and
`docs/dex_hff/hff_pipeline_summary.xlsx` (`Stage Funnel` sheet) and writes the six JSON
files the app reads from `docs/data/`:

- `dict.json` — codebook (levels for every coded column, financing-function and
  outcome-domain category lists, summary meta)
- `studies.json` — one row per analysis-population record (columnar)
- `function.json` / `outcome.json` — multi-value junction tables (a study can carry more
  than one financing function or outcome domain, so it's counted in every one)
- `geo.json` — study↔country↔year pairs, matched against the reused country reference
- `countries.json` — country reference (income, region, population, DALYs, health
  spending) with study counts/ratios recomputed from `geo.json`
- `content.json` — hero text, glance tiles, the pipeline-stage funnel (from the
  `Stage Funnel` sheet), and the Explorer's filter/chart registries

Rebuild: `python docs/dex_hff/build_data.py` (reads the CSV/xlsx, overwrites `docs/data/*.json`,
prints a validation report — record counts, unmatched geography names, category counts).

`docs/dex_hff/build_texts.py` writes one small JSON shard per country to `docs/data/texts/`
(`{"s": [...], "title": [...], "abstract": [...]}`), used by the Country Profile tab's
"click a study, read it" feature. Title/abstract text for the full population is ~94MB, too
large to bundle upfront, so shards are fetched lazily by the client only when a study point
in that country is clicked, and cached client-side after the first fetch. Run it after
`build_data.py` (it reads back `studies.json`/`geo.json`/`countries.json` to figure out which
studies belong to which country). Unlike `docs/dex_hff/`'s raw CSV/xlsx inputs, the shards it
writes under `docs/data/texts/` are published output and are committed like the rest of
`docs/data/*.json`.

Runtime deps are pinned jsdelivr CDNs: plotly.js-dist-min 2.35.2, tom-select 2.3.1,
noUiSlider 15.8.1, Google Fonts (Newsreader + Inter). No build step, no bundler.

## What changed from the HEE dashboard, and why

HEE's fields describe *economic evaluations of interventions* (does the study use a QALY,
is it model-based, does it report an ICER). HFF's extraction describes *financing-function
studies* (revenue raising, pooling, purchasing, etc.) and has no equivalent methodology —
so those fields were replaced rather than relabeled:

| HEE field | HFF replacement | Why |
|---|---|---|
| `econ_eval_type` | `financing_function` (multi-value) | The core classification dimension; a study can be tagged with more than one function, so it's a junction table (`function.json`) like HEE's old disease groups, not a single column. |
| `qaly_label` (uses QALY?) | *dropped* | QALYs measure benefit gained from an intervention in a cost-utility analysis. HFF studies aren't intervention cost-effectiveness evaluations, so "did this study use a QALY" isn't a meaningful question here. |
| `model_label` / `has_icer` / `has_threshold` / `oa_label` | `type_of_analysis`, `data_type`, `data_source`, `has_doi` | HEE's model-vs-measured / ICER / threshold / open-access signals don't apply; these are the closest real HFF equivalents (quantitative/qualitative, data provenance, whether a DOI was recovered). |
| — (new) | `outcome_domain` (multi-value) | A second multi-value dimension (financial protection, efficiency, equity, etc.) with its own junction table (`outcome.json`), filterable/countable the same way as `financing_function`. |

**DALYs, population and health spending are kept, but only as country-level reference
data** (from the reused World Bank/IHME country table) — denominators for "studies per
100k DALYs" style charts, not fields extracted from the HFF studies themselves. This is
the same role they played in HEE's country profile.

**Geography note:** country matching reuses HEE's 154-country reference table. A handful
of real geographies named in the HFF extraction — Taiwan, Israel, Kazakhstan, Cuba, Iceland,
Luxembourg, Fiji, Bhutan, Maldives, Solomon Islands among them — aren't in that reference
table and are therefore excluded from country-level views (map, country profile) while
still counted everywhere else. Extending the reference table with these countries' income
group/population/DALY/spending data would need a separate data-sourcing pass; `build_data.py`
prints the full unmatched-name list (with counts) so this can be prioritized.

## The opportunity matrix (`fig_funder_opportunity.png`)

Modeled on HEE's `fig_funder_opportunity.webp` — a heatmap crossing disease area against
income group, showing each disease's share of research divided by its share of disease
burden (GBD DALYs) within that income level. Deep red means research is thin relative to
burden; blue means it's disproportionately well covered.

HFF can't build that exact chart: there's no `funder` field in the extraction, and there's
no burden dataset broken out *by financing function* (DALYs measure disease burden, not
which financing function needs more research). So the two axes here are different, and the
"burden" denominator is replaced with a within-corpus reference:

- **Rows — disease category.** Built from `mesh_theme`, but only for records where
  `mesh_source == "pubmed"` (a true MeSH term list from PubMed metadata, not the
  OpenAlex-fallback subject hierarchy used elsewhere, e.g. in `fig_topic_landscape.png`).
  Each record's semicolon-separated MeSH terms are keyword-matched
  (`MESH_DISEASE_KEYWORDS` in `build_figures.py`) against 11 broad groups modeled on HEE's
  own MeSH C-tree groupings (Infectious, Neoplasms, Cardiovascular, Chronic respiratory,
  Digestive, Neurological & mental, Musculoskeletal, Skin, Maternal & neonatal, Metabolic &
  nutritional, Injuries) and assigned to whichever category has the most matching terms.
  Demographic/methods MeSH terms (*Humans*, *Female*, *United States*, *Cross-Sectional
  Studies*, ...) never match anything, which is correct — they aren't diseases. Records
  with no matching term (most financing-function papers aren't about a specific disease at
  all — they're about Medicaid, insurance design, PFM reform, etc.) are excluded from this
  figure entirely: 34.9% of the 20,164 PubMed-MeSH records matched a category, 7,031
  studies in total.
- **Columns — financing function**, the same multi-value tag as everywhere else in the
  dashboard (a study counts toward every function it's tagged with).
- **Cell value** = *(that disease's share of tags for that function)* ÷ *(that function's
  overall share across all 7,031 disease-tagged studies)*. A value of 2× means that disease
  area is tagged with that function twice as often as the disease-tagged corpus is on
  average; 0.5× means half as often. This is a **relative-emphasis index within HFF's own
  data**, not a burden-adjusted "evidence gap" the way HEE's version is — the footnote baked
  into the image itself says so explicitly, so the two charts are never confused for
  measuring the same thing.
- **Grey cells** (`n=`) have fewer than 5 studies for that specific disease/function
  pairing — too few to report a ratio, same threshold logic as HEE's own "<15" rule, scaled
  down for HFF's smaller disease-tagged subset.

Latest build: infectious-disease studies are tagged *Recurrent financing (supply chain)*
2.1× as often as the disease-tagged average (vaccines, HIV/TB/malaria commodities — supply
chains are central to how that research frames financing), while musculoskeletal studies
are tagged *Revenue Raising* only 0.32× as often — the widest gaps in either direction.
Row order is sorted by each disease's mean ratio across its non-grey cells, so the top of
the chart reads as the areas getting relatively *less* financing-function-specific research
attention than average, and the bottom as relatively *more*.
