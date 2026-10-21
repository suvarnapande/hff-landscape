"""Re-render approved figure wording using native plotting code and unchanged data.

Run after apply_copy.py. Builder JSON writes are diverted into local staging;
only configured gallery PNGs are saved there. Review PNGs before copying them to
docs/figures. No dataset or analytical JSON is modified by this renderer.
"""
import inspect
import json
import re
import runpy
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.text import Text

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STAGE=HERE/'rendered'
STAGE.mkdir(exist_ok=True)
(STAGE/'data').mkdir(exist_ok=True)
COPY=json.loads((HERE/'figure_copy.json').read_text(encoding='utf-8'))
TARGETS=set(COPY)-{'fig_glance_regions.html','fig_topicmap.png','fig_topicmap_income.png'}
original_save=Figure.savefig
original_write=Path.write_text
footnotes={}

def normalized(t):
    return ''.join(str(t).replace('\\$', '$').split())

def save(self, fname, *args, **kwargs):
    name=Path(str(fname)).name
    if name.startswith('_tmp_'):
        return original_save(self,fname,*args,**kwargs)
    if name not in TARGETS:
        return
    frame=inspect.currentframe().f_back
    meta=None
    while frame:
        g=frame.f_globals
        meta=g.get('FIG_META',{}).get(name)
        if meta:
            break
        if g.get('fname')==name and all(k in g for k in ('headline','desc','finding')):
            meta=(g['headline'],g['desc'],g['finding'])
            break
        frame=frame.f_back
    if not meta:
        raise RuntimeError('No native header metadata for '+name)
    if isinstance(meta,dict):
        # These builders expose only the combined caption. Header text appears
        # first in fig.texts, followed by description and finding.
        originals=[t.get_text() for t in self.texts if t.get_position()[1] >= .85][:3]
    else:
        originals=list(meta)
    all_text=self.findobj(match=Text)
    for text in all_text:
        value=text.get_text()
        if name=='fig_methods_characteristics.png' and value=='Mixed data types' and text.get_fontsize()>10:
            value='Mixed data\ntypes'
            text.set_fontsize(10)
        value=value.replace('The 15 largest evidence deficits','The 15 largest gaps against this benchmark')
        value=value.replace('priority zone','Below comparison lines').replace('underfunded relative to its burden','spending below the burden comparison line')
        if 'Below comparison lines' in value and 'spending below the burden comparison line' in value:
            value='Spending below line\nResearch below benchmark'
            text.set_fontsize(8)
        value=value.replace('studies short of a need-proportional share','studies below the combined benchmark')
        text.set_text(value)
    targets=[]
    for source in originals:
        targets.append(next((t for t in all_text if normalized(t.get_text())==normalized(source) and normalized(source)),None))
    if not targets[0]:
        raise RuntimeError('Header text not found for '+name)
    self.canvas.draw()
    renderer=self.canvas.get_renderer()
    headers=[t for t in targets if t]
    boxes=[t.get_window_extent(renderer) for t in headers]
    x_px=min(b.x0 for b in boxes)
    y_px=min(b.y0 for b in boxes)
    x,y=self.transFigure.inverted().transform((x_px,y_px))
    available=self.get_figwidth()*max(.35,.98-x)
    width=max(35,int(available*72/(10*.55)))
    caption=textwrap.fill(COPY[name]['caption'],width,break_long_words=False)
    headline=textwrap.fill(COPY[name]['title'],max(32,int(available*72/(16*.6))),break_long_words=False)
    title=targets[0]
    desc=targets[1] if len(targets)>1 else None
    finding=targets[2] if len(targets)>2 else None
    if finding and finding is not desc: finding.set_text('')
    if desc:
        desc.set_text(caption.replace('$',r'\$'))
        desc.set_fontsize(10)
        desc.set_transform(self.transFigure)
        desc.set_position((x,y))
        desc.set_va('bottom')
        desc.set_ha('left')
        desc.set_fontweight('normal')
    offset=((caption.count('\n')+1)*10*1.3+12)/(self.get_figheight()*72)
    title.set_text(headline)
    title.set_fontsize(16)
    title.set_transform(self.transFigure)
    title.set_position((x,y+offset))
    title.set_va('bottom')
    title.set_ha('left')
    footer_text=[]
    for t in self.texts:
        if t.get_position()[1]<=.07 and t.get_fontsize()<=9.5 and t.get_text() and t.get_position()[0]<.5:
            old=t.get_text()
            footer_text.append(' '.join(old.split()))
            t.set_text('')
    if footer_text:
        first=footer_text[0].split('. ')[0].replace('HFF','health financing').rstrip('.')
        short=first+'. '+COPY[name]['warning']
        self.text(.01,.015,textwrap.fill(short.replace('$',r'\$'),max(65,int(self.get_figwidth()*11)),break_long_words=False),fontsize=7.6,ha='left',va='top',color='#59616a')
    footnotes[name]=footer_text
    kwargs['bbox_inches']='tight'
    kwargs.setdefault('pad_inches',.15)
    print('Editorial render:',name,flush=True)
    return original_save(self,STAGE/name,*args,**kwargs)

def write(self,text,*args,**kwargs):
    resolved=self.resolve()
    if resolved.parent==ROOT/'docs/data':
        return original_write(STAGE/'data'/self.name,text,*args,**kwargs)
    return original_write(self,text,*args,**kwargs)

Figure.savefig=save
Path.write_text=write
sys.path.insert(0,str(ROOT/'docs/dex_hff'))
if __name__=='__main__':
    for name in ['build_figures_v2_4.py','build_funder_types_v2_4.py','build_fcas_outcomes_v2_4.py','build_open_access_v2_4.py']:
        sys.argv=[name,'--only',','.join(sorted(TARGETS))]
        runpy.run_path(str(ROOT/'docs/dex_hff'/name),run_name='__main__')
    original_write(STAGE/'original_footnotes.json',json.dumps(footnotes,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Rendered',len(footnotes),'configured figures',flush=True)
