"""Re-render the figures requiring final editorial layout corrections."""
import json
import runpy
import sys
import render_copy as renderer
renderer.TARGETS={f for f in renderer.TARGETS if not f.startswith('fig_map_')}|{'fig_worldmap.png','fig_map_oa_author_v5.png'}
for name in ['build_figures_v2_4.py','build_funder_types_v2_4.py','build_fcas_outcomes_v2_4.py','build_open_access_v2_4.py']:
    sys.argv=[name,'--only',','.join(sorted(renderer.TARGETS))]
    runpy.run_path(str(renderer.ROOT/'docs/dex_hff'/name),run_name='__main__')
path=renderer.STAGE/'original_footnotes.json'
combined=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
combined.update(renderer.footnotes)
renderer.original_write(path,json.dumps(combined,ensure_ascii=False,indent=2),encoding='utf-8')
print('Final layout corrections rendered',flush=True)
