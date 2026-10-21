# Plain-language review of the HFF evidence map

Review date: 13 October 2026. Editorial review only; no website, dataset, figure or existing source file was changed.

Scope: all 75 configured gallery figures (74 PNGs inspected visually, plus the regional HTML figure reviewed from its source); all 15 theme descriptions; Overview, Explorer, Country landscape/profile, Scope definitions, help content and limitations. Overview reuses gallery images. Hidden Wellcome and unused figure assets are outside the active-page inventory. Browser connection was unavailable, so this is a source-and-image review, not a live rendering or keyboard-accessibility test. Small image footnotes were reviewed where legible; important numerical inconsistencies below should be verified against the generating data before editing.

## Changes to prioritise

1. **Separate research quantity from evidence quality.** The hero says evidence is “strong”, but the map counts studies and classifications. Proposed heading: **“Explore what health financing research covers — and where gaps remain.”** Add: “The map shows how much research was identified. It does not assess study quality or establish which policies work.” Source: `docs/index.html:48`.
2. **Correct claims before simplifying them.** The health-aid caption says $9.5bn is larger than $11bn; author-affiliation charts infer leadership; a recent-publication share is labelled fastest growth; several rankings imply funding recommendations. These need correction, not concealment in notes.
3. **Use plain display labels while preserving official categories.** “Financing topics”, “Outcomes studied”, “Countries covered”, “Free to read”, and “Routine records” are easier to scan. Keep official definitions accessible so simplified names do not change category meaning.
4. **Give each figure one short main message.** A descriptive title, one plain finding, and one “How to read this chart” sentence are usually enough. The current PNGs often repeat the title, method and finding again in the page caption. Remove repeated prose from the page or regenerate the images with shorter copy.
5. **Separate chart help from technical notes.** A visible “How to read” line should explain dots, colours, widths and denominators. A labelled information button can expose methods, equations and data sources. Do not hide limits that change what a reader would conclude.

## Content that needs verification or correction

| Location | Finding | Proposed action |
|---|---|---|
| `fig_dah_cuts_source.png`, gallery caption | “$9.5bn ... alone larger than the $11.0bn net drop” is arithmetically wrong. | Verify source amounts; if retained, say about 86% of the net decline. Update both PNG and page caption. |
| `fig_authorship_pattern.png`, `fig_authorship_by_function.png`, ownership theme | “Who leads”, “rarely led locally” and “foreign-led” infer leadership from affiliations. | Describe author locations; do not infer lead authorship, research control, nationality or capacity from these measures. |
| `fig_map_authorship.png` | Blue is described as mostly domestic, but measure is at least one locally based author. | Use “Higher share of studies with an author based in the country studied”. |
| `fig_map_growth.png` | Share published since 2018 is described as fastest growth. | Describe recency; calculate growth separately if that claim is wanted. |
| Topic map figures | Caption states largest group has 9,317 studies; topic-map legend displays 6,020. The maps explicitly use an older 36,495-study dataset. | Reconcile counts and retain a prominent “Earlier dataset” label; do not hide the version distinction. |
| Topic-group explanation and rank figure | Section note says 49 groups; `fig_theme_rank.png` footer says 56 emergent themes. | Verify actual fitted version and align the explanation, ranking and map. |
| `fig_funder_function_heatmap.png` | Caption calls percentages shares of tag mentions, whereas image colourbar says shares of tagged studies; displayed rows exceed 100%. | Verify actual calculation; label the denominator consistently. |
| `fig_forest.png` caption | Local-author odds sentence compares low-income studies with low-income studies; the stated reference group is high income. | Correct reference after verification. Avoid converting odds ratios to probability differences. |
| `fig_map_bivariate.png` | Embedded headline says six countries; example sentence lists five. | Confirm the full set or label the listed countries as examples. |
| `fig_glance_regions.html:190` | “Search dates: xx” is unfinished public copy. | Supply actual protocol dates, or a truthful date-availability statement. Do not invent a date. |
| `docs/index.html:71`, `docs/app.js` trend copy | Mid-2026 search timing is asserted, while the regional figure says search dates are not in web data. | Check the protocol. Keep the partial-year warning; distinguish search date from map update date. |
| `docs/index.html:447`, `:506`, footer | Human verification wording differs: “human verification” versus “not independently human-verified”. Methodology panel is not exposed through the current Scope tabs. | Establish the actual extent of human checking and use one short, consistent statement visible from Overview/help. |
| Funding priority scorecards | Disease-burden/spending benchmarks are presented as underfunding, funding priorities or an exact shortfall of studies. | Describe assumptions and comparisons. These are not validated estimates of how much funding or research is required. |
| Correlation figures | “Only clearly negative” is used despite other negative point estimates. | Remove “only clearly” or define and substantiate the criterion. Correlation alone does not establish statistical significance. |
| `OTHER_OUTCOME_NOTE` in `docs/app.js:14`, used at `:1058` and `:2530` | Some outcome-figure notes use older theme counts (e.g. service use/access 4,518), whereas the current explainer/figure shows 8,189. | Reconcile populations, versions and counts. The old note is actively rendered in figure modals and some gallery cards; update or remove it rather than leaving two unexplained sets of counts. |

## What stays visible, goes into notes, or can be omitted

**Keep visible:** the meaning of dots/colours/bands; what the percentage is out of; whether categories overlap; whether a figure covers a subset or older dataset; preliminary/forecast status; partial-year warnings; no-data versus zero-studies distinctions; “no studies identified in this map”; benchmark assumptions; affiliations do not establish leadership; associations do not show cause and effect.

**Technical notes:** UMAP/HDBSCAN, embeddings, MeSH matching, OpenAlex taxonomy, model names and consensus rules, first-listed-tag selection, exact equations, log transformations, Gini coefficients, correlation coefficients, adjusted odds ratios and regression adjustments, historical income classifications, region-allocation rules, name-normalisation rules and minimum-count thresholds. Keep the operational consequence of a threshold visible when it explains omitted countries/categories.

**Usually omit from the main narrative:** chart-type names such as lollipop, dumbbell and alluvial; “Alternative view” without a preceding view; processing history about September versus October; “proportional area makes concentration immediately visible”; repeated numbers already printed on bars; emphatic metaphors such as “punch above”, “fallen off a cliff”, “boom/bust” and “evidence deserts”. Retain necessary definitions and limitations, in the appropriate location.

## Page narrative and controls

| Where | Current wording | Suggested display wording / action |
|---|---|---|
| Overview hero | Evidence is strong | Research coverage is extensive; use the proposed heading above. |
| Main navigation | Thematic analysis; Explorer; Scope | Optional: Research themes; Explore studies; What the map covers. Retain existing names if users already know them, with short descriptions. |
| Overview trend toggle | Cumulative | Total so far. Keep “Per year” alongside it. |
| Overview map heading | Where the evidence is about | Where the research is focused. |
| Overview disease card | What gets evaluated? | Which financing topics are studied for each disease area? |
| Overview/Explorer tile | DOI or URL available | Studies with a publication link. Explain a link may lead to a landing page, not free full text. |
| Overview/Scope | Outcome domains mapped | Outcomes studied, with official outcome-domain definitions in help. |
| Overview/Explorer | Geographic scope | Countries covered: one, several, regional/global or not stated. Avoid hiding the “not stated” proportion. |
| Analysis-approach cards | Quantitative / Qualitative / Mixed methods | Numerical analysis / Interviews, text or experiences / Both, with official labels in help. These describe approaches, not study quality. |
| Funding overview | Government and multilateral; Unclassified | Governments and international organisations; Funder type not identified. Keep “Among studies reporting a funder; categories may overlap”. |
| Explorer filter | Financing function | Financing topic. Give short, faithful explanations of all categories. |
| Explorer filter | Outcome domain | Outcome studied. Explain Other and Unclear next to the control or in a short help panel. |
| Explorer filter | Region (WHO) | World region (WHO grouping). Keep that this is a specific grouping; exceptions go into notes. |
| Explorer filter | Income group (in publication year) | Country income group. Keep “At the time the study was published” as helper text. |
| Explorer controls | Metric / Variable / X axis / Y axis | Show / Compare / Horizontal measure / Vertical measure. Keep Group by and Reset filters. |
| Explorer filter note | Every filter combines | Only studies matching all your selections are shown. Keep multiple-topic/country counting explanation below. |
| Explorer dropdowns | Nothing (total), None, Era, Reports a DOI | All studies, No grouping, Publication period, Has a DOI identifier. Do not replace DOI-only measures with DOI-or-URL measures. |
| Explorer/country metrics | Per 100k DALYs | Studies relative to disease burden; retain “per 100,000 healthy years lost” as a visible unit and define DALYs in help. |
| Country/spending measures | PPP US$; per US$1bn | Spending adjusted for differences in purchasing power; per US$1 billion. Keep actual currency and year. Do not mix these PPP measures with other figures’ constant 2023 US-dollar measures. |
| Country heatmap | Row shares; carry ... tag | Explain “Of studies about [outcome], X% also cover [financing topic]”. Keep this direction clear: this country heatmap conditions on outcomes, while another gallery heatmap conditions on financing topics. |
| Country profiles | Income-group mean / median | Average / middle value among countries in the same income group. Keep which comparison is used; they are different statistics. |
| Country strip | Reflects whatever filters are set | Uses your Explorer filters. Put a visible active-filter summary near the chart; the other country panels may use a different population. |
| Scope financing definitions | Long WHO passages | Lead with one plain sentence and an example; put full official definitions under “Full definition and source”. Preserve distinctions among pooling, purchasing and procurement. |
| Scope outcome definitions | Code this outcome ...; Do not code ... | Move coding instructions into technical notes. Keep definitions and distinctions users need to interpret the categories. |
| Outcome help | Long list of eight formal names | Use short display names plus one-line meanings; link to official definitions. |
| Other-outcome explainer | Coded; outcome domains; catastrophic out-of-pocket payments | Classified; outcome groups; health bills that cause financial hardship. Retain the useful specific examples distinguishing access from equitable access. |
| Limitations | LLM-based; ecological, not causal | AI classified study titles and summaries, so some labels may be wrong. Country-level comparisons do not show that one factor causes another. Clarify human checking accurately. |

## Theme names and introductory narratives

Each proposed introduction gives the reader a concrete question. Keep detailed sources and methods in technical notes, while retaining the subset warnings listed above.

| Current theme | Proposed theme name | Proposed short introduction |
|---|---|---|
| Financing functions & outcomes | Financing topics and outcomes studied | Which parts of health financing receive the most research attention, and what do these studies measure? |
| Topic clusters | Research topics | Explore groups of studies on similar subjects, and the research fields they belong to. |
| Disease focus | Disease areas studied | See which disease areas appear in the research and how the topics studied differ between them. Only studies with disease classifications are included in these figures. |
| Methods & data | How studies were carried out | See how studies were designed and what kinds of data they used. |
| Geographic coverage | Where research is focused | Compare the countries covered by research, the age of the studies and the approaches they use. |
| Geographic inequalities | Differences in research coverage | Compare how research is distributed with countries’ populations and disease burden. These comparisons highlight possible gaps within the studies identified by this map. |
| Research ownership & collaboration | Author locations and collaboration | See where authors are based and how often teams include authors based in the country studied. Author locations do not establish who led the research. |
| Research funding | Who funds the research? | See which organisations are named as funders and which topics and outcomes their studies examine. Funding details are available for only part of the map. |
| Fragile & conflict-affected settings | Research in settings affected by fragility or conflict | See which settings are covered, how research coverage has changed and which outcomes are studied. Countries are classified using the World Bank list for each publication year. |
| The financing backdrop | Health aid and spending | Explore how international health aid and spending per person have changed. Dashed lines show forecasts. |
| Where financing and evidence diverge | Research, health spending and disease burden | Compare research coverage with spending and disease burden. These are exploratory comparisons, rather than estimates of how much research or funding each country needs. |
| How research priorities differ | How research topics differ between countries | See how the topics and outcomes studied differ between countries that spend more or less on health. |
| How research responds over time | Research and health aid over time | Compare trends in research and international health aid. Similar trends do not show that changes in aid caused changes in research. |
| USA sensitivity analysis | Checking the influence of US studies | See whether the patterns change when studies about the United States are left out. |
| Open access & author countries | Free access and author locations | See how often studies are free to read and where their authors are based. Access status could be checked only for studies with a DOI. |

For the grouped menu headings, consider **Health aid, spending and research** instead of Global financing context; **Authors and free access** instead of Authorship & access; **Research topics and disease areas** instead of Topic clustering & disease focus; and **Countries and research coverage** instead of Geography. Keep the descriptions consistent with the renamed navigation.

## Suggested short labels, with official terms preserved in definitions

| Official category | Short display label | Plain explanation |
|---|---|---|
| Revenue raising | Raising health funds | How money is raised through taxes, insurance contributions, direct payments or other sources. |
| Pooling | Sharing financial risk | How prepaid funds are combined so people share the cost of care. |
| Purchasing | Paying for health services | How payers decide what services to pay for and how to pay providers. |
| Benefits decisions | Deciding what care is covered | Which services and people are covered, and under what conditions. |
| Public financial management | Managing public health budgets | How public health funds are planned, spent, tracked and accounted for. |
| Recurrent financing for procurement and distribution of supply chain inputs | Funding health supplies and delivery | Ongoing funding for procuring and delivering supplies and running those systems. |
| Capital investment: infrastructure | Investing in facilities, equipment and digital systems | Funding the development or improvement of health infrastructure. |
| Capital investment: other health system inputs | Investing in the workforce and health-product production | The project definition covers training/growing the workforce and producing health products; confirm exact label scope before changing it. |
| Overall | Health financing overall | Add the actual coding definition; do not assume this means all financing topics. |
| Equitable distribution of health-system resources | Fair access to care and health resources | Differences between groups in how care, resources and benefits are distributed. Studies of access alone do not establish equity. |
| Efficiency in the use of resources | Making good use of resources | What services or health benefits are achieved with the money and other resources used. |
| Quality of service provision | Quality of care | Whether services meet appropriate standards and support better health. |
| Improved level and distribution of health | Health improvement and its distribution | Health outcomes and differences in health across people or groups. |
| Responsiveness to citizens | How care responds to people’s needs | Service users’ experiences and perspectives; not simply provider opinions. |
| Financial protection | Protection from financial hardship | Whether paying for health care causes financial difficulty. |
| Transparency and accountability | Openness and accountability | Whether decisions and spending can be examined and those responsible held to account. |
| Other | Other outcomes | Identifiable outcomes outside the eight named groups, not poor-quality or irrelevant studies. |
| Unclear | Outcome could not be identified | The available title and abstract did not contain enough information. |

Use low- and middle-income countries on first mention, then lower-income countries only where its meaning is unambiguous. Avoid mixing L&MICs, LMICs and poor/rich countries. In authorship figures, always refer to where authors are based, not their personal income.

## Suggested information-button pattern

Figure heading → one plain-language finding → chart → one visible “How to read” line → a button labelled **Technical notes** (an information icon plus text).

Open the notes by click/tap and keyboard, not hover alone. Give the button an accessible name such as “Technical notes for research coverage by country”. Use clear sections: What is counted; How it was calculated; Data sources; Limitations. Keep chart titles, units and meaningful limitations in downloaded PNGs too: page-only help will be lost on export. Include a short source/version footnote in the image; put long reproducibility details in the webpage notes.

Example main text: **“More recent studies are free to read.”** “Among studies whose access status could be checked, the share rose from 39% in 2010 to 74% in 2025.” Visible caveat: “Studies without a DOI could not be checked.” Technical notes can explain the OpenAlex lookup and denominator in detail.

## Figure-by-figure recommendations

These are proposed display titles, not changes to classifications or numerical results. Notes specify details to move or claims to verify. Update the image text and gallery caption together when implementing.


### Financing functions & outcomes

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_function_bar.png` — Financing function | Which health financing topics are studied most? | Replace the image headline “punch above the per-function average”. Remove the average line unless it serves a clear question; count labels are enough. Shorten financing-category names. |
| `fig_function_second_opinion_v2_2.png` — Financing functions with and without second-opinion labels | How an extra classification check changes the results | Move this entire figure to classification technical notes. Explain the extra AI review there; model names, 7,298 records, label provenance and sensitivity belong there. |
| `fig_outcome_lollipop.png` — Outcome domain | What do the studies measure? | Explain Other beside the chart: “Measures outside the eight named outcome groups”. Avoid presenting Other as a single substantive outcome or saying it dominates. |
| `fig_function_outcome_heatmap.png` — Function vs. outcome | Which outcomes are studied for each financing topic? | Keep darker colour = a larger share, plus the actual denominator, visible. Move “row shares”, “tags” and classification exclusions into notes. |
| `fig_function_time_lines.png` — Financing-function mix over time | How the topics studied have changed over time | Keep “A study may cover several topics” visible. Replace function mix/tagged studies with topics/eligible studies, preserving the actual base. |
| `fig_method_stream.png` — Financing-function output over time | How research on each financing topic has grown | This counts topic assignments, not unique studies. Keep that distinction visible. Avoid “output” and “across the board” unless every series supports that statement. |
| `fig_alluvial.png` — Evidence flow: design to function to outcome | How study methods, financing topics and outcomes overlap | Explain wider bands = more studies. Move first-listed-tag selection to notes, but visibly state that only one topic and outcome are shown per study; first-listed does not establish primary importance. |
| `fig_outcome_other_themes_v5.png` — 'Other' outcomes are led by access and spending | What is included in “Other” outcomes? | Good central question. Shorten the theme names and explain HTA as assessment of health technologies. Move September/October processing history into notes; retain missing-theme coverage. |
| `fig_outcome_trend_v5.png` — Health outcomes and financial protection gain ground | How the outcomes studied have changed over time | Use “Studies increasingly examine health improvement and financial hardship”. Avoid “gain ground” suggesting health itself improved; keep the population and years visible. |

### Topic clusters

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_theme_rank.png` — Top 20 research themes | The 20 largest groups of research topics | Replace emergent/cluster size with groups of similar studies. Use readable topic names with original keywords in notes. Verify the topic-group count: the explanatory note says 49, while this image footer says 56. |
| `fig_topicmap.png` — Thematic landscape | Groups of studies with similar topics | Move abstract embeddings, UMAP and HDBSCAN into notes. Say closer points have more similar abstracts, with projection limitations in notes. Keep a visible older-dataset badge. Verify the caption’s 9,317 against the plotted legend’s 6,020. |
| `fig_topicmap_income.png` — Themes by income skew | Which topic groups focus on lower-income countries? | Replace income skew/skews with share about low- and middle-income countries. Use percentage ticks. Retain a visible older-dataset badge; describe the single-country subset beside the chart. |
| `fig_topic_landscape.png` — Topic landscape | Which research fields do the studies belong to? | Explain bar length = number of studies. Move taxonomy/domain/subfield hierarchy and OpenAlex assignment method to notes. Distinguish research fields from the project’s topic groups. |
| `fig_topic_landscape_treemap.png` — Topic landscape (treemap) | Which research fields have the most studies? | Explain larger boxes = more studies. Remove “proportional area makes that concentration immediately visible”. Offer this clearer view before the radial chart; preserve the externally assigned category names. |

### Disease focus

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_disease_circular.png` — The disease focus of HFF research | Which disease areas are studied? | Use cancer instead of Neoplasms and heart and blood-vessel conditions instead of Cardiovascular in display labels, with official terms in notes. Keep disease-classified subset coverage visible. |
| `fig_disease_method.png` — How each disease area is evaluated | Which financing topics are studied in each disease area? | “Evaluated” implies evaluation that the figure does not establish. Replace “leans hardest on Pooling” with a direct share statement. MeSH matching goes into notes. |
| `fig_funder_opportunity.png` — The opportunity matrix | Which financing topics receive more attention in each disease area? | Replace opportunity matrix/disproportionately with “more or less common than across the disease-classified studies”. Keep colour meaning and comparison baseline visible; formula and ratio thresholds go into notes. |
| `fig_transition.png` — L&MICs research: communicable to NCD shift | How the disease areas studied in lower-income countries have changed | Expand NCD to non-communicable diseases and give an example. Move epidemiological-transition classes and MeSH to notes. This shows research composition, not a change in population disease burden. |
| `fig_funder_trajectory.png` — L&MICs research share, era 1 to era 2 | How research about lower-income countries has changed by disease area | Replace era 1/era 2 with 2010–2017/2018–2026, pp with percentage points. Keep small-category caution visible; avoid drawing strong conclusions from very small groups. |
| `fig_map_disease.png` — The disease atlas | Where each disease area has been studied | Replace atlas/busiest/systems with country coverage. Keep the disease-classified subset visible. Explain equal colour changes represent multiples; move log transform and MeSH details into notes. |

### Methods & data

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_methods_characteristics.png` — Methodological characteristics of included studies | How the studies were carried out | Preserve the helpful questions already embedded in the image. Define observational, experimental and qualitative in plain language. Split the crowded multi-panel image or enlarge the labels, especially mixed/unclear data types. |

### Geographic coverage

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_worldmap.png` — Where the evidence is about | Where health financing research is focused | Replace “where the evidence is about” and per capita with studies per 10 million people. Keep no-studies/no-data colour meaning visible; diverging palette/log scale/projection belong in notes. |
| `fig_top_countries.png` — Top 20 countries | The 20 countries with the most studies | Mostly clear. Replace study-country pairs in the main sentence with studies about each country, plus “Studies covering several countries count in each”. |
| `fig_income_bar.png` — Study-country pairs by income group | Research coverage by country income group | Use “Studies counted for each country they cover”; retain multiple-country counting visibly. Historical income classifications and missing-group exclusions belong in notes. |
| `fig_map_growth.png` — Where the evidence is youngest | Which countries have more recent research? | A high share published since 2018 does not by itself show the fastest growth. Remove faster-growing/growing fastest unless annual growth is separately calculated; keep the date window. |
| `fig_map_method.png` — The dominant type of analysis | The most common research approach in each country | Replace modal category with most common approach. Define quantitative as numerical analysis and qualitative as interviews/text/experiences. Keep the five-study minimum visible. |

### Geographic inequalities

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_glance_regions.html` — (Un)equal weight at a glance | Research coverage relative to health spending | Replace “(Un)equal weight”. Retain the good explanation that a high ratio can reflect low spending. Use billion in full. Put region assignment and currency adjustments in notes. Replace the unfinished “Search dates: xx”. |
| `fig_map_bivariate.png` — Where high burden meets low evidence | Countries with high disease burden and little research in this map | Replace tertiles with low/middle/high thirds. Keep an explicit colour key and definition of disease burden. Image says six countries, but the caption names five: verify and reconcile. |
| `fig_map_burden.png` — Research intensity against disease burden (map) | Research relative to disease burden, by country | Define DALYs beside the figure as healthy years lost through illness or early death. Keep denominator units and no-data meaning; move the median centring and transforms into notes. |
| `fig_map_deserts.png` — Evidence deserts | Countries with no studies identified in this map | Replace evidence deserts/no HFF evidence at all with no included studies identified. Search and country-matching limits mean this cannot establish that no research exists. |
| `fig_burden.png` — Research intensity vs. disease burden | How research coverage compares with disease burden | Avoid “the poorest countries carry the most disease and the least research”, which is broader than the shown per-burden comparison. Keep the 15-fold median comparison scoped to included countries; explain bubble size. |
| `fig_deficit.png` — Studies vs. a burden-proportional share | How study counts compare with a disease-burden benchmark | Avoid implying an exact number of studies is needed. Say “6,647 below this comparison benchmark”, if verified. Keep benchmark assumption and direction of bars visible; formula goes into notes. |
| `fig_injustice.png` — Research relative to disease burden | Research share compared with disease-burden share | Explain above/below the comparison line visibly. Move log2 ratio and calculation to notes. The proportional relationship is an illustrative benchmark, not an established ideal. |
| `fig_equity_time.png` — L&MICs research share over time | How the share of research about lower-income countries has changed | Remove “real progress” unless making an explicit value judgement. Keep the 25% to 41% finding. Explain that the 83% burden line is a comparison benchmark with a different denominator. |
| `fig_inequality.png` — Evidence concentration among L&MICs | How research is concentrated across lower-income countries | Lead with the five-country/46% result after checking its population and weighting. Move Gini=0.42 and Lorenz-curve construction to notes; make cumulative axes understandable. |
| `fig_forest.png` — Adjusted odds ratios by income group | How research approaches and local authorship differ by income group | Move the forest plot and logistic regression to technical notes or an advanced analysis area. Main text can describe associations. Odds ratios are not probability ratios; fix the sentence comparing low-income local authorship to itself. Retain “This does not show cause and effect”. |

### Research ownership & collaboration

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_map_authorship.png` — Who studies whom | How often do studies include an author based in the country studied? | At least one local author does not mean mostly domestic authorship. Replace blue=mostly domestic/red=produced from outside with higher/lower share including a local author. Define local as institutional location, not nationality. |
| `fig_authorship_pattern.png` — Who leads research about each setting | Where are authors of research about each income group based? | Replace “Who leads” and the image’s “rarely led locally”: affiliations do not establish research leadership. Keep local-only/mixed/outside-only definitions visible and missing-affiliation coverage nearby. |
| `fig_authorship_by_function.png` — Local authorship, by financing function | Local authorship by health financing topic | Replace the image’s “most foreign-led” with “The Overall category has the lowest share with a local author”. Define Overall; remove judgemental “Only 84%”. |
| `fig_authorship_outcome_heatmap.png` — Local authorship, by outcome domain | Author-team locations by outcome studied | Replace local-only team with authors based only in the country studied in the legend. Keep mixed-team meaning visible; move row-share terminology into notes. |
| `fig_collab_chord.png` — Cross-income co-authorship | Collaboration between authors in different income groups | Replace cross-income co-authorship/wholly high-income-authored with authors based in countries in the same/different income groups. Explain wider bands = more collaborating studies. Counting across multiple group pairs belongs in notes. |
| `fig_funder_capacity.png` — Where to build local research capacity | Where studies include fewer authors based locally | Local authorship is an imperfect proxy for research capacity, not a direct capacity assessment. Replace “Where to build” with the descriptive title and keep the proxy limitation visible. |

### Research funding

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_funder_types_v5.png` — National governments fund most studies; industry funds few | Which types of organisations fund the research? | State “Among studies that name a funder” in the headline/subtitle. These are recorded acknowledgements, not funding amounts. Keep multi-funder overlap visible; move classification/name matching to notes. |
| `fig_funder_funders_treemap.png` — The top research funders | The most frequently named research funders | Use the existing helpful overview label. Replace “Alternative view” because a reader may not have seen another view. Keep larger boxes = more studies; merge-name rules go into notes. |
| `fig_funder_function_heatmap.png` — What each top funder pays for | Which financing topics appear in each funder’s studies? | Replace “What each top funder pays for”: study counts are not grant amounts. Verify the denominator: caption says share of tag mentions; image colourbar says share of tagged studies and rows exceed 100%. |
| `fig_funder_outcome_heatmap.png` — What each top funder's research finds | Which outcomes are studied in each funder’s research? | Replace “What ... research finds”: the chart shows outcomes examined, not findings or effects. Keep multi-outcome overlap and the eligible base visible. |
| `fig_funder_trend.png` — Which funders are gaining ground | How the funders named in studies have changed over time | Replace gaining ground and +3.1pp with share increased by 3.1 percentage points. Keep only studies naming funders visible; this cannot establish changes in funding amounts. |
| `fig_funder_authorship_alluvial.png` — Funder to financing function to authorship | How funders, financing topics and author-team locations connect | Explain wider bands = more studies and show the restricted 535-study base. Move single-funder selection and first-listed topic choice to notes; do not imply all funded research is represented. |
| `fig_funder_scorecard.png` — Funding priority scorecard | Where research coverage is low relative to disease burden | Replace funding priority scorecard: the figure is a descriptive benchmark, not a validated funding recommendation. Keep no studies identified separate from finite ratios; log2/formula go into notes. |

### Fragile & conflict-affected settings

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_fcas_countries_v5.png` — Nigeria and Ethiopia carry the FCAS evidence base | Countries affected by fragility or conflict with the most studies | Expand FCAS; prefer the neutral category rather than “fragile country”. Explain classification uses the World Bank list for the publication year; keep country overlap clear. |
| `fig_fcas_trend_v5.png` — FCAS research is growing, but list changes exaggerate the jump | How research in settings affected by fragility or conflict has changed | Say part of the increase reflects changes in the country list, rather than “exaggerate the jump”. Retain annual-list versus fixed-country comparison visibly; matching details go into notes. |
| `fig_outcome_by_context_v5.png` — FCAS studies look more like low-income than high-income evidence | Which outcomes are studied in settings affected by fragility or conflict? | Avoid “look more like ... evidence”. Use the specific financial-protection and resource-use shares. Keep overlapping groups visible; FCAS is not a mutually exclusive income category. |

### The financing backdrop

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_dah_trend.png` — Development assistance for health, 1990–2030 | How international aid for health has changed | Replace “fallen off a cliff” and DAH with international aid for health. Clearly mark preliminary values and forecasts. Keep dollar price year; source model details go into notes. |
| `fig_dah_cuts_source.png` — The 2025 aid cuts, by source | Which donors reduced health aid in 2025? | CORRECT before rewriting: $9.5bn is smaller than $11.0bn, not larger. If both figures are verified, say “The US accounted for about 86% of the net decline”. Retain preliminary-data status. |
| `fig_health_spending_income.png` — Health spending per person, by income group | How health spending per person differs by country income group | Replace “the average person ... has ... spent on their health” with average spending per person. Keep historical/forecast distinction and adjusted currency units; move log scaling into notes. |

### Where financing and evidence diverge

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_aid_vs_evidence_region.png` — Aid vs. evidence, by region | How regional shares of health aid and research compare | Expand aid acronym and study-country pairs. Keep “Uses different regional groups from the other maps” visible; detailed approximation rules go into notes. Do not imply aid shares must match research shares. |
| `fig_research_vs_spending_country.png` — Research intensity vs. health spending, by country | How health spending and research coverage are related | Use countries spending more per person tend to have more studies per person. Move log-log correlation r=0.63 to notes; retain observational/non-causal caution. |
| `fig_funder_scorecard_combined.png` — Funding priority scorecard: burden, spending and research together | Research coverage compared with disease burden and health spending | Replace priority scorecard/underfunded/understudied with an exploratory comparison. Keep “The ranking depends on how need is defined” visible. Need-index formula, weights and exact deficits belong in notes; avoid prescribing 5,233 missing studies as an actual requirement. |
| `fig_funder_scorecard_expenditure.png` — Funding priority scorecard: health expenditure edition | Research coverage compared with health spending | Explain this is a different benchmark from disease burden: high-spending countries can rank as having less research relative to spending. Avoid a funding-priority interpretation; formulas and study-count differences belong in notes. |

### How research priorities differ

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_function_share_quartile.png` — Financing-function mix by spending quartile | How financing topics differ between lower- and higher-spending countries | Replace quartiles/Q1–Q4 with lowest/lower-middle/upper-middle/highest spending groups, avoiding confusion with income groups. Keep visible that shares are normalised topic assignments, not unique-study percentages. |
| `fig_outcome_share_quartile.png` — Outcome-domain mix by spending quartile | How outcomes studied differ between lower- and higher-spending countries | Use the same spending-group labels. Keep normalised shares visible; move country-average and re-normalisation steps to notes. Replace +3.8pp with percentage points. |
| `fig_function_share_facets.png` — Each function's research share vs. health spending | How each financing topic relates to health spending | Replace facets with small charts if needed. Main explanation: each dot is a country. Move linear fitting, r and log transform to notes; retain association warning. |
| `fig_function_share_lollipop.png` — Ranked: function share vs. health spending | Which financing topics are more common in higher-spending countries? | Move the correlation plot to advanced/technical analysis or explain positive/negative directions plainly. “Only clearly negative” conflicts with other negative estimates unless clear has a statistical definition; verify or remove. |

### How research responds over time

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_functions_vs_dah_index.png` — Every financing function vs. real-world aid | How health financing research and international health aid changed over time | Replace “every function” with the six topics shown; explain 100 means the 2010–2011 starting level. Move index construction and correlation to notes. “Research responds” implies a causal response not established here. |
| `fig_revenue_vs_dah.png` — Revenue-Raising research vs. real-world aid | Research on raising health funds alongside international aid | Say the two series moved together in some years, not research tracks/responds to aid. Keep two different vertical scales obvious. Correlation and inflation adjustments go into notes. |
| `fig_function_bump_eras.png` — Financing-function ranks, aid boom vs. bust | How the ranking of financing topics changed between two periods | Replace aid boom/bust/crashed with 2015–2019 and 2022–2025. Rankings do not establish that aid caused the change; explain rank 1 = most studies. |

### USA sensitivity analysis

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_function_share_lollipop_no_usa.png` — Ranked: function share vs. health spending (excluding USA) | Research–spending relationships after excluding US studies | Advanced analysis. Replace sensitivity analysis with “Checking whether the US changes the pattern”. Put correlation and log-spending details in notes; explicitly state studies about the US are removed, not US-authored studies. |
| `fig_function_share_lollipop_all_vs_no_usa.png` — Paired lollipop: all studies vs. excluding USA | Do the research–spending patterns change without US studies? | Avoid paired lollipop as a user-facing title. This overlaps the next figure; select one comparison for the main page and put the alternative in technical notes. |
| `fig_function_share_r_no_usa_dumbbell.png` — Correlation sensitivity: all studies vs. excluding USA | How research–spending relationships change without US studies | Avoid dumbbell/correlation sensitivity in headings. Use a clear before/after legend. Prefer one of this and the preceding figure; exact r changes belong in notes. |
| `fig_function_share_no_usa_dumbbell.png` — Global financing-function mix: all studies vs. excluding USA | How the topics studied change without US studies | Replace global financing-function mix and USA-mapped with topics/all studies excluding studies about the US. Explain this counts topic assignments. Keep before/after legend; detailed removal rules go into notes. |
| `fig_function_share_no_usa_delta.png` — Change in financing-function mix after excluding USA | Which topic shares change after excluding US studies? | Write percentage points in full. Keep the largest 4.3-point pooling change. Remove “showing how small” or define a practical threshold; consideration of size is interpretive. |

### Open access & author countries

| Figure / current page title | Proposed title | Flag / placement |
|---|---|---|
| `fig_map_oa_author_v5.png` — Where open-access research comes from | How often studies by authors in each country are free to read | Define author country as institution location. Keep checked-study denominator visible. Replace “beat the average study” with above the overall checked-study share; distinguish weighted overall share from the average of country shares. |
| `fig_oa_trend_v5.png` — Open access has become the norm | How the share of studies free to read has grown | Prefer free to read, with open access in parentheses. Keep “among studies whose access status could be checked” and the DOI-based coverage visible, rather than only in a help icon. |
| `fig_oa_author_income_v5.png` — Research with lower-income authors is more often open access | How free access differs by author-team location | Replace lower-income authors with authors based in low- and middle-income countries; personal income is not measured. Keep mixed-team and DOI-checked subset definitions visible. |
| `fig_oa_author_countries_v5.png` — Authors in lower-income countries publish open access more often | Free access among studies with authors based in each country | Replace “Authors ... publish ... more often” with a statement about included publications. Keep top-25-country scope visible; clarify mean of country shares versus study-weighted overall mean in notes. |

## Suggested implementation order

First correct factual/interpretive problems and add visible coverage warnings. Then simplify Overview, Explorer and Country labels. Next introduce one consistent technical-notes pattern and shorten captions. Finally regenerate the PNG text, simplify long category labels and remove redundant alternative charts from the main narrative. Re-check exported images and a live browser after changes.
