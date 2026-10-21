"""Update only text on legacy topic maps using their ORIGINAL dataset/model.

The original six analytical JSON files are read from their historical git
snapshot, not today's study data. All writes are staged locally. Actual point
coordinates and the old topic assignments are retained by the native v5 builder.
"""
import json
import runpy
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import plotly.basedatatypes as pbd

import render_copy as renderer

renderer.TARGETS={'fig_topicmap.png','fig_topicmap_income.png'}
old_read=Path.read_text
snapshots={}
for name in ['dict.json','studies.json','function.json','outcome.json','geo.json','countries.json','content.json']:
    result=subprocess.run(['git','show',f'f59156c:docs/data/{name}'],cwd=renderer.ROOT,capture_output=True,check=True)
    snapshots[name]=result.stdout.decode('utf-8')

def read(self,*args,**kwargs):
    if self.resolve().parent==renderer.ROOT/'docs/data' and self.name in snapshots:
        return snapshots[self.name]
    return old_read(self,*args,**kwargs)

def placeholder(self,file,*args,**kwargs):
    # Only legacy scatter maps are requested; the native builder computes other
    # panels for shared intermediates but their geographic images are unused.
    plt.imsave(str(file),np.ones((40,80,3)))

Path.read_text=read
pbd.BaseFigure.write_image=placeholder
sys.argv=['build_figures_v5.py']
runpy.run_path(str(renderer.ROOT/'docs/dex_hff/build_figures_v5.py'),run_name='__main__')
renderer.original_write(renderer.STAGE/'legacy_footnotes.json',json.dumps(renderer.footnotes,ensure_ascii=False,indent=2),encoding='utf-8')
print('Legacy topic maps rendered from historical data',flush=True)
