"""Apply approved editorial copy without changing study data or classifications.

Run from the repository: python docs/dex_hff/plain_language_review/apply_copy.py
The before_edit snapshot is the immutable input for this editorial pass.
"""
import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
tree = ast.parse((HERE / 'build_review.py').read_text(encoding='utf-8'))
recs = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='recommendations' for t in n.targets))
original = json.loads((HERE / 'before_edit/docs/data/content.json').read_text(encoding='utf-8'))

CAPTIONS = [
[
'Benefits decisions and purchasing have the most studies. A study may cover several financing functions.',
'Adding labels from the extra classification check changes each function’s share only slightly.',
'“Other” includes identifiable outcomes outside the eight named groups. A study may examine several outcomes.',
'Each row shows the outcomes examined by studies covering that financing function. Darker cells mean a larger share; shares can exceed 100%.',
'Benefits decisions accounted for 27% of eligible studies at the start of the period and 24% at the end. A study may cover several functions.',
'Financing-function assignments grew 1.9 times between 2010 and 2025. This counts functions assigned to studies, rather than unique studies.',
'Wider bands represent more studies. Each study is shown with one financing function and one outcome, selected from its recorded labels.',
'Service use, access and coverage, and spending, prices and funding are the largest groups within “Other”.',
'The share examining health improvement rose from 8% to 13%; financial protection rose from 7% to 9%, between 2010 and 2025.'
],
[
'The largest groups concern insurance programmes and medicines. Labels show characteristic words from each group.',
'Each dot represents a study; nearby dots have more similar abstracts. This is a map of topics, not a geographic map.',
'Colours show how often each topic group’s single-country studies examine low- and middle-income countries.',
'Longer bars represent more studies in each research field. The fields come from publication metadata.',
'Larger boxes represent more studies. Economics and Econometrics is the largest research field among studies with a field label.'
],
[
'The figures cover studies assigned a disease category, rather than all studies in the map. Bar length shows the share in each disease area.',
'Each row shows the financing functions covered by studies in that disease area. A study may cover several functions, so shares can exceed 100%.',
'Blue cells show financing functions that are more common in a disease area than across disease-classified studies; red cells show functions that are less common.',
'Among disease-classified studies about low- and middle-income countries, non-communicable diseases became a larger share of research between 2010 and 2025.',
'Dots show 2010–2017 and arrowheads show 2018–2026. An arrow to the right means a larger share of that disease area’s research concerns low- and middle-income countries.',
'The maps show where studies in each disease area were identified. Darker colours mean more studies.'
],
['Cross-sectional and correlational studies are the most common design. Routine administrative records are the most common data source.'],
[
'The map compares studies per 10 million people. Multi-country studies count in every country they cover.',
'The United States has the most studies in the map. Studies covering several countries count in each country.',
'High-income countries account for the largest share of country coverage. A study counts once for each country it examines.',
'Colour shows the share of a country’s studies published in 2018–2026. A higher share means more recent research, rather than necessarily faster growth.',
'Colour shows the most common analysis approach among each country’s studies. Countries with fewer than five studies are not classified.'
],
[
'Compare studies relative to health spending and explore the regional profiles. A high number of studies per dollar can reflect low spending, rather than a large research base.',
'The colours combine low, middle and high levels of disease burden and study counts. Red identifies countries with high burden and relatively few studies in this map.',
'The map shows studies per 100,000 healthy years lost through illness or early death. Blue indicates more research relative to burden; red indicates less.',
'Djibouti has disease-burden data but no included study naming it. This does not establish that no research exists there.',
'The middle-ranked high-income country has 15 times as many studies per unit of disease burden as the middle-ranked low-income country.',
'This comparison asks what study counts would look like if countries’ research shares matched their shares of disease burden. It is an illustrative benchmark.',
'Countries below the comparison line have a smaller share of studies than their share of disease burden. This is a benchmark, rather than a recommended research allocation.',
'The share of single-country studies about low- and middle-income countries rose from 25% in 2010 to 41% in 2025.',
'Research is unevenly distributed across low- and middle-income countries. The five most-studied countries account for 46% of their evidence base.',
'Research approach and the inclusion of locally based authors differ by country income group. These adjusted associations do not show cause and effect.'
],
[
'The map shows how often studies include at least one author based in the country studied. Author location refers to institutional affiliation, not nationality or leadership.',
'Among studies about low-income countries with author-location information, 19% have only locally based authors, 50% have mixed teams and 31% have no locally based author.',
'The share including a locally based author ranges from 84% for the Overall category to 95% for Purchasing. These shares do not identify research leaders.',
'Each row shows where authors are based for studies examining that outcome. Mixed teams include authors based both inside and outside the country studied.',
'Bands link income groups whose authors collaborate on the same studies. Wider bands mean more studies; within-group studies are excluded from the bands.',
'Countries differ in the share of studies that include a locally based author. This measure alone does not establish local research capacity.'
],
[
'Among studies that name a funder, 53% name national governments. A study may name more than one funder; these are study counts, not amounts of funding.',
'Larger boxes show funders named by more studies. Studies naming several funders count once for each.',
'Each row shows the share of that funder’s studies covering each financing function, among studies assigned a function. Shares can exceed 100% because functions overlap.',
'Each row shows which outcomes are examined in that funder’s studies. It shows what was studied, rather than what the research found.',
'The lines show each funder’s share of studies naming a funder in that year. They do not measure the amount of money provided.',
'Wider bands represent more studies connecting a funder, one recorded financing function and an author-team location. Only 535 eligible studies are shown.',
'The chart compares countries’ research shares with their shares of disease burden. The ranking depends on this benchmark and does not establish funding priorities.'
],
[
'Nigeria and Ethiopia appear in 38% of studies covering settings classified as affected by fragility or conflict. Multi-country studies may appear under several countries.',
'Research coverage increased. Part of the increase reflects changes in the World Bank country list; the fixed-country comparison also shows growth.',
'Compared with studies about high-income countries, studies in these settings more often examine financial protection and less often examine resource use.'
],
[
'International health aid fell from its 2021 peak. The 2025 estimate is preliminary; dashed lines show forecasts for 2026–2030.',
'The United States accounts for the largest reduction shown, at $9.5 billion. The net decline across all sources is $11.0 billion; 2025 estimates are preliminary.',
'Average health spending per person is much higher in high-income countries. Dashed lines show forecasts; dollar amounts are expressed in 2023 prices.'
],
[
'Sub-Saharan Africa receives 53% of health aid but accounts for 10% of study-country counts. These are different measures and need not have matching shares.',
'Countries spending more on health per person tend to have more studies per person. This association does not show that spending causes more research.',
'This exploratory comparison combines disease burden, health spending and research coverage. Its rankings depend on how the comparison benchmark is defined.',
'This chart compares research coverage with health spending. A gap against spending is different from a gap against disease burden and does not establish a funding priority.'
],
[
'Benefits decisions take a larger share of financing-function assignments in higher-spending country groups. The four groups are based on health spending, not country income.',
'Resource-use outcomes take a larger share in higher-spending country groups. These are normalised category shares, rather than percentages of unique studies.',
'Each dot is a country. The small charts show how research shares vary with spending per person; fitted lines show associations, not effects.',
'Positive values mean a function is more common in countries spending more per person; negative values mean it is less common. These associations do not establish cause and effect.'
],
[
'Lines compare changes from the 2010–2011 starting level, set to 100. Similar trends do not show that changes in aid caused changes in research.',
'The chart places research on raising health funds alongside international health aid. The two lines use different vertical scales and do not establish a causal relationship.',
'Compare the ranking of functions by average annual study count in 2015–2019 and 2022–2025. Rank 1 means the most studies.'
],
[
'This repeats the research–spending comparison after removing studies about the United States. Studies are removed by country studied, not author location.',
'The two sets of dots compare the full dataset with the dataset excluding studies about the United States. The pattern changes little.',
'The two sets of dots compare associations before and after removing studies about the United States. They do not measure causal effects.',
'The chart compares shares of financing-function assignments with and without studies about the United States. A study may have several function assignments.',
'Pooling shows the largest change, a decline of 4.3 percentage points in its share of financing-function assignments.'
],
[
'The map shows the share of checked studies that are free to read, for studies with at least one author based in each country.',
'Among studies whose access status could be checked, the share free to read rose from 39% in 2010 to 74% in 2025.',
'Studies with authors based in low- and middle-income countries are more often free to read. “Mixed” teams include authors based in both high-income and lower-income countries.',
'The chart compares free access among studies with authors based in each of the 25 most active author countries. A study can count in several countries.'
]
]

WARNINGS = {
    'Topic clusters':'',
    'Disease focus':'Disease classifications are available for 7,874 of the 53,362 studies, so these figures describe a subset.',
    'Research ownership & collaboration':'Author locations are available for only part of the evidence base and do not establish who led the research.',
    'Research funding':'Funder information is recorded for only part of the evidence base. Missing information does not mean a study had no funding.',
    'Open access & author countries':'Access status was checked using DOI identifiers. Studies without a DOI could not be checked.',
}
FIXES = {
    'fig_dah_cuts_source.png': [(' — alone larger than the ', '; compared with the ')],
    'fig_map_growth.png': [('newer, faster-growing evidence base', 'more recent evidence base'), ('The evidence base is growing fastest', 'The share of recent studies is highest')],
    'fig_map_authorship.png': [('Blue = mostly domestic; red = mostly produced from outside.', 'Blue = a higher share with at least one locally based author; red = a lower share.')],
    'fig_funder_function_heatmap.png': [("share of that funder's tag mentions", "share of that funder's studies with a financing function"), ("financing-function tags are", "studies cover")],
    'fig_forest.png': [('0.07× the odds of Low income studies having a local author', '0.07× the odds of high-income studies having a local author')],
}
copy = {}
for sec, rs, cs in zip(original['gallery'],recs,CAPTIONS):
    assert len(sec['figs']) == len(rs) == len(cs), sec['title']
    for f, (title,_), caption in zip(sec['figs'],rs,cs):
        title = title.replace('health financing topics', 'financing functions').replace('financing topics', 'financing functions').replace('financing topic', 'financing function')
        if sec['title'] in {'Financing functions & outcomes','How research priorities differ','USA sensitivity analysis'}:
            title = title.replace('topics studied','financing functions studied').replace('topic shares','function shares')
        old = f['caption']
        for a,b in FIXES.get(f['file'],[]): old=old.replace(a,b)
        if f['file'] in {'fig_topicmap.png','fig_topicmap_income.png'}:
            old = 'Earlier dataset: HSF extraction, September 2026. Uses 36,495 studies and the earlier topic model; the current dataset lacks the coordinates needed to rebuild these maps. Position uses a two-dimensional UMAP projection of abstract embeddings, coloured by HDBSCAN topic group or the share of single-country studies in lower-income countries. Projected distances are an approximation of abstract similarity.'
        if f['file'] in {'fig_function_share_lollipop.png','fig_function_share_lollipop_no_usa.png'}:
            old=old.replace('the only clearly negative relationship','a negative association')
        if 'scorecard' in f['file']:
            old = 'This is an exploratory proportional-share benchmark, not a validated recommendation about funding or an estimate of the number of studies required. ' + old.replace('underfunded and understudied','below the spending and research comparison lines').replace('priority','comparison').replace('need','benchmark')
        f.update(title=title,caption=caption,technical_notes=[old],warning=WARNINGS.get(sec['title'],''))
        if f['file'].startswith('fig_topicmap'):
            f['warning']='Earlier dataset: these two maps use the September 2026 set of 36,495 studies, not the current 53,362-study map.'
        if f['file']=='fig_outcome_other_themes_v5.png':
            f['warning']='6,827 studies classified as Other could not be assigned a theme and are not shown. A study may appear in several themes.'
        if f['file']=='fig_function_second_opinion_v2_2.png':
            f['technical_only']=True
        if f['file']=='fig_forest.png':
            f['warning']='The chart shows adjusted odds ratios, not probability ratios. Associations do not establish cause and effect.'
        copy[f['file']] = {k:f[k] for k in ['title','caption','warning']}

blurbs = {
'Financing functions & outcomes':'Explore which financing functions receive the most research attention and what outcomes the studies examine.',
'Topic clusters':'Explore groups of studies on similar subjects and the research fields they belong to.',
'Disease focus':'See which disease areas appear in the research and which financing functions are studied. These figures cover studies with disease classifications.',
'Geographic inequalities':'Compare how research is distributed with countries’ populations and disease burden. The comparisons highlight possible gaps among the studies identified by this map.',
'Research ownership & collaboration':'See where authors are based and how often teams include an author based in the country studied. Author locations do not establish who led the research.',
'Research funding':'See which organisations are named as funders and which functions and outcomes their studies examine. Funder information is available for only part of the map.',
'The financing backdrop':'Explore how international health aid and spending per person have changed. Dashed lines show forecasts.',
'Where financing and evidence diverge':'Compare research coverage with health spending and disease burden. These exploratory comparisons do not estimate how much research or funding a country needs.',
'How research responds over time':'Compare trends in research and international health aid. Similar trends do not establish cause and effect.',
'USA sensitivity analysis':'See whether the patterns change when studies about the United States are left out.',
'Open access & author countries':'See how often studies are free to read and where their authors are based. Access status could be checked only for studies with a DOI.'}
for s in original['gallery']: s['blurb']=blurbs.get(s['title'],s['blurb'])
for entries in original['registries'].values():
    for entry in entries:
        if isinstance(entry,dict) and entry.get('label')=='Outcome domain':
            entry['label']='Outcomes studied'
# Keep section identifiers stable: app.js uses them for routing and grouping.
(ROOT/'docs/data/content.json').write_text(json.dumps(original,ensure_ascii=False,allow_nan=False),encoding='utf-8')
(HERE/'figure_copy.json').write_text(json.dumps(copy,ensure_ascii=False,indent=2),encoding='utf-8')
print('Editorial titles, captions, warnings and technical notes prepared for',len(copy),'figures')
