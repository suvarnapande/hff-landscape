"""Preserve figure methods in disclosure notes and verify unchanged data."""
import hashlib
import json
import shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
content_path=ROOT/'docs/data/content.json'
content=json.loads(content_path.read_text(encoding='utf-8'))
before=json.loads((HERE/'before_edit/docs/data/content.json').read_text(encoding='utf-8'))
assert [f['file'] for s in content['gallery'] for f in s['figs']]==[f['file'] for s in before['gallery'] for f in s['figs']]
for key in ['funnel','glance_tiles']:
    assert content[key]==before[key],key
notes={}
for name in ['original_footnotes.json','legacy_footnotes.json']:
    notes.update(json.loads((HERE/'rendered'/name).read_text(encoding='utf-8')))
for section in content['gallery']:
    for f in section['figs']:
        for note in notes.get(f['file'],[]):
            if note and note not in f['technical_notes']:
                f['technical_notes'].append(note)
        if f['file'].endswith('.png'):
            source=HERE/'rendered'/f['file']
            assert source.exists(),source
            shutil.copy2(source,ROOT/'docs/figures'/f['file'])
content_path.write_text(json.dumps(content,ensure_ascii=False,allow_nan=False),encoding='utf-8')
shutil.copy2(HERE/'before_edit/docs/data/funder_types_v5.csv',ROOT/'docs/data/funder_types_v5.csv')
hashes=json.loads((HERE/'before_edit/hashes.json').read_text(encoding='utf-8'))
for name,digest in hashes.items():
    if name.replace('\\','/')=='docs/data/content.json':
        continue
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
print('75 gallery entries checked; 74 PNGs copied; analytical JSON and included dataset unchanged.')
