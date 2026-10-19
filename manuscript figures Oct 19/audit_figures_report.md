# Figure audit

PASS 17 | DIFF 5 | INFO 4

| Status | Check | Expected | Actual | Note |
|---|---|---|---|---|
| DIFF | countries.json study counts vs raw | 185 values | 184 match | United Kingdom: 1976 vs 1951 |
| DIFF | Study-country pairs: site total vs distinct pairs in raw | 47,693 | 47,668 | site geo.json keeps a pair once per matching place name, so a study naming e.g. England and Scotland counts twice for the United Kingdom |
| DIFF | Fig 1 map_per10m.csv: studies per country | 185 values | 184 match | GBR: 1976 vs 1951 |
| DIFF | Fig 1 map_per10m.csv: rate per 10 million | 184 values | 183 match | GBR: 284.3697382244161 vs 280.7719429533582 |
| DIFF | Glance 1 map_per100k_dalys.csv: rate per 100,000 DALYs | 182 values | 181 match | GBR: 8.859762201437949 vs 8.747670068322591 |
| PASS | Glance 1 caption: countries with a rate | 182 | 182 |  |
| PASS | Headline: studies | 53,411 | 53,411 |  |
| PASS | Headline: countries with at least one study (data) | 184 | 184 |  |
| PASS | Headline: studies naming a country | 44,248 | 44,248 |  |
| PASS | Headline: financial protection, all studies (%) | 8.29 | 8.29 |  |
| PASS | Headline: studies with a recorded outcome | 41,309 | 41,309 |  |
| PASS | Headline: financial protection, studies with a recorded outcome (%) | 10.71 | 10.71 |  |
| PASS | Headline: most studied function | Benefits decisions | Benefits decisions |  |
| PASS | Headline: its share of function-tagged studies (%) | 24.86 | 24.86 |  |
| PASS | Headline: focus on low- and middle-income countries (%) | 35.38 | 35.38 |  |
| PASS | Headline: open access (%) vs raw is_oa among studies with a DOI | 63.70 | 63.71 | headline comes from open_access_v5.json (OpenAlex match); raw is_oa is a second source |
| PASS | Region profiles region_functions.csv: function shares and n | 108 values | 108 match |  |
| PASS | Region profiles region_fp.csv: financial protection shares (both bases) | 12 values | 12 match |  |
| PASS | Region profiles region_trend.csv: country coverage to 2025 | 224 values | 224 match |  |
| PASS | Leading-function map leading_function.csv: status and leading function | 185 values | 185 match |  |
| PASS | Fig 8 aid_vs_research.csv: research shares (distinct pairs) | 7 values | 7 match | tolerance 0.1 pp: the CSV counts site pairs (see the pairs check above) |
| PASS | Fig 8 aid_vs_research.csv: aid shares | 7 values | 7 match |  |
| INFO | make_figures.R: MS_COUNTRIES | 198 | 184 in the data | typed in from the manuscript text; differs from the data drawn in the figure |
| INFO | make_figures.R: MS_PAIRS | 47488 | 47,668 in the data | typed in from the manuscript text; differs from the data drawn in the figure |
| INFO | make_glance_figures_v2.R: MS_COUNTRIES | 198 | 184 in the data | typed in from the manuscript text; differs from the data drawn in the figure |
| INFO | make_glance_figures_v2.R: MS_PAIRS | 47488 | 47,668 in the data | typed in from the manuscript text; differs from the data drawn in the figure |
