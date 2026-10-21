import json
import subprocess
from pathlib import Path

def head(path):
    return subprocess.check_output(['git', 'show', 'HEAD:' + path]).decode('utf-8')

def stage(path, text):
    sha = subprocess.check_output(['git', 'hash-object', '-w', '--stdin'], input=text.encode('utf-8')).decode().strip()
    subprocess.run(['git', 'update-index', '--cacheinfo', '100644', sha, path], check=True)

path = 'docs/data/content.json'
base = json.loads(head(path))
current = json.loads(Path(path).read_text(encoding='utf-8'))
new = next(f for g in current['gallery'] for f in g['figs'] if f['file'] == 'fig_function_bar.png')
old = next(f for g in base['gallery'] for f in g['figs'] if f['file'] == 'fig_function_bar.png')
old.clear()
old.update(new)
stage(path, json.dumps(base, ensure_ascii=False))
path = 'docs/dex_hff/build_figures_v2_4.py'
base = head(path)
current = Path(path).read_text(encoding='utf-8')
start = 'set_headline(ax, f"{n_above}'
end = '             "fig_function_bar.png")'
a = base.index(start)
z = base.index(end, a) + len(end)
x = current.index(start)
y = current.index(end, x) + len(end)
stage(path, base[:a] + current[x:y] + base[z:])
