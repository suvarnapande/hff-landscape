"""Explain the Kosovo DALY gap in the existing gallery notes; no data changes."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
path = root / 'docs/data/content.json'
content = json.loads(path.read_text(encoding='utf-8'))
direct = {
    'fig_map_bivariate.png', 'fig_map_burden.png', 'fig_map_deserts.png',
    'fig_burden.png', 'fig_deficit.png', 'fig_injustice.png',
    'fig_inequality.png', 'fig_funder_capacity.png', 'fig_funder_scorecard.png',
    'fig_funder_scorecard_combined.png',
}
note = ('Kosovo has 8 included studies but no comparable GBD 2023 DALY estimate, '
        'so it is excluded from this figure, which requires disease-burden data.')
special = {
    'fig_equity_time.png':
        'Kosovo has 8 included studies but no comparable GBD 2023 DALY estimate. '
        'Its studies can contribute to the research shares where eligible, '
        'but Kosovo is absent from the disease-burden benchmark.',
    'fig_worldmap.png':
        'Kosovo has 8 included studies but no comparable GBD 2023 DALY estimate. '
        'This map uses the country subset with disease-burden data, so Kosovo is '
        'omitted even though the displayed rate is based on population.',
}
updated = []
for section in content['gallery']:
    for figure in section['figs']:
        filename = figure['file']
        explanation = note if filename in direct else special.get(filename)
        if not explanation:
            continue
        notes = figure.setdefault('technical_notes', [])
        if explanation not in notes:
            notes.append(explanation)
        warning = figure.get('warning', '')
        if explanation not in warning:
            figure['warning'] = (warning + ' ' + explanation).strip()
        updated.append(filename)
assert set(updated) == direct | set(special)
path.write_text(json.dumps(content, ensure_ascii=False, allow_nan=False), encoding='utf-8')
print('Added visible coverage notes and Technical notes to', len(updated), 'figures.')
