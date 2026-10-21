"""Render only the financing-function count figure and update its explanation."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
builder = ROOT / 'docs/dex_hff/build_figures_v2_4.py'
sys.path.insert(0, str(builder.parent))
sys.argv = [str(builder), '--only', 'fig_function_bar.png']
source = builder.read_text(encoding='utf-8').split('# --- fig_function_second_opinion_v2_2:')[0]
scope = {'__file__': str(builder), '__name__': '__main__'}
exec(compile(source, str(builder), 'exec'), scope)
headline, desc, finding = scope['FIG_META']['fig_function_bar.png']
path = ROOT / 'docs/data/content.json'
content = json.loads(path.read_text(encoding='utf-8'))
for group in content['gallery']:
    for figure in group['figs']:
        if figure['file'] == 'fig_function_bar.png':
            figure['title'] = headline
            figure['caption'] = desc + ' ' + finding
            figure['technical_notes'] = [
                'Above-average means more studies than the mean across the nine financing functions: 66,331 function assignments divided by 9, or approximately 7,370 studies per function.',
                'The five above the average are benefits decisions (13,088), purchasing (11,738), pooling (10,568), revenue raising (8,309) and public financial management (7,572).',
                'Study counts measure research volume, not importance or quality. A study can cover more than one function.',
                'Base: 66,331 function assignments across 53,362 studies.'
            ]
path.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
print(headline)
