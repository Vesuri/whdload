from pathlib import Path
import json,sys,bisect,re,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];base=int(r['probe'],16);rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 if pc is None:return -1
 i=bisect.bisect_right(keys,pc)-1
 return rows[i]['old']+pc-rows[i]['actual'] if i>=0 and pc<rows[i]['actual']+rows[i]['size'] else pc
build=Path(r['slave']).parent;listing=(build/'fine/fine.list').read_text();accepted=[int(x[1],16) for x in re.finditer(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+:\s+adda.w d3,a0',listing,re.M) if sy['FF1RenderBitmap']<=int(x[1],16)<sy['FF1RenderBitmapControl']];assert len(accepted)==1
trace=barto.load(p/'detail.bin');active=None;call=None;cost=0;draws=[]
for f in trace.fields:
 for pc,c,g in trace.instructions(f):
  irq=(g[16]>>8)&7;n=canon(pc)
  if not irq:
   if pc==base+sy['B8Draw']:active=[];call=None
   if active is not None:
    if n==0x24ae0:assert call is None;call=dict(start=cost,cpu=False)
    if call is not None:
     if pc==base+accepted[0]:call['cpu']=True
     if n==0x24d80:call['us']=(cost-call.pop('start')+c)/14.18758;active.append(call);call=None
    if pc==base+sy['B8Frames']-2:assert call is None;draws.append(active);active=None
  cost+=c
out=dict(complete_draws=len(draws),calls_per_draw=[len(d) for d in draws],cpu_glyphs_per_draw=[sum(c['cpu'] for c in d) for d in draws],glyph_cpu_mean_us=sum(c['us'] for d in draws for c in d if c['cpu'])/max(1,sum(c['cpu'] for d in draws for c in d)),total_bitmap_ms_per_draw=sum(c['us'] for d in draws for c in d)/1000/len(draws))
(p/'bitmap-analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
