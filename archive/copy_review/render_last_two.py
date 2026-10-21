"""Final label fitting on the methods panel and combined benchmark chart."""
import json
import runpy
import sys
import render_copy as renderer
renderer.TARGETS={'fig_methods_characteristics.png','fig_funder_scorecard_combined.png'}
sys.argv=['build_figures_v2_4.py','--only',','.join(sorted(renderer.TARGETS))]
runpy.run_path(str(renderer.ROOT/'docs/dex_hff/build_figures_v2_4.py'),run_name='__main__')
path=renderer.STAGE/'original_footnotes.json'
notes=json.loads(path.read_text(encoding='utf-8'))
notes.update(renderer.footnotes)
renderer.original_write(path,json.dumps(notes,ensure_ascii=False,indent=2),encoding='utf-8')
print('Final two labels fitted',flush=True)
