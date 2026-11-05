#!/usr/bin/env python3
# Per top-level B8Draw call: inclusive time split into blitter-wait spin, IRQ
# service and CPU work, plus WaitBlit spin by native caller site. Uses the same
# gap/IRQ attribution as analyze_hi25_profile.py.
from pathlib import Path
import sys,json,bisect,collections,struct,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];probe=int(r['probe'],16);host=int(r['host'],16)
rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 i=bisect.bisect_right(keys,pc)-1
 if i>=0 and pc<rows[i]['actual']+rows[i]['size']:return rows[i]['old']+pc-rows[i]['actual']
 return pc
listing=(Path(r['slave']).parent/'fine/fine.list').read_text()
calls={}
lo,hi=sy['B8Draw'],sy['B8Frames']
for m in re.finditer(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+:\s+(jsr|bsr\.[lw])\s+([^\s;]+)',listing,re.M):
 a=int(m[1],16)
 if lo<=a<hi:calls[probe+a]=m[3]
mem=bytearray((p/'start.bin').read_bytes());mem+=bytes(0x200000-len(mem))+(p/'start-fast.bin').read_bytes()
def op(pc):return struct.unpack_from('>H',mem,pc)[0] if pc is not None and pc+2<=len(mem) else 0
glues=set();at=0x200000
while True:
 at=mem.find(bytes.fromhex('514f40d7007c0700'),at)
 if at<0:break
 glues.add(at);at+=2
hw=host+r['host_symbols']['gfx_WaitBlit'];hwe=hw+0x3a
entry=probe+sy['B8Draw'];end=probe+sy['B8Frames']-2
t=barto.load(p/'detail.bin');n_fields=len(t.fields);cyc_ms=20.031886677085037/(sum(f.cycles for f in t.fields)/n_fields)
accepted_per=collections.defaultdict(collections.Counter);accepted_sites=collections.defaultdict(collections.Counter);accepted_blits=collections.Counter();complete=0
per=collections.defaultdict(collections.Counter);sites=collections.defaultdict(collections.Counter);ncalls=collections.Counter()
indraw=False;cur='setup';depth=0;pending=0;last_cpu=None;draws=0;in_wait=False;site=None;blits=collections.Counter()
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==0x7fffffff:pending+=cost;continue
  cost+=pending;pending=0
  if pc in glues:depth+=1
  if pc==entry:
   indraw=True;cur='setup';draws+=1
   per=collections.defaultdict(collections.Counter);sites=collections.defaultdict(collections.Counter);blits=collections.Counter()
  if indraw and not depth and pc in calls:cur='%s@%x'%(calls[pc],pc-probe);ncalls[cur]+=1
  if indraw and not depth and pc==probe+sy['B8_65728']:cur='beam wait'
  if depth:cat='irq'
  elif pc is None:cat='stop'
  elif hw<=pc<hwe or 0x2a130<=canon(pc)<0x2a140:cat='wait'
  else:cat='cpu'
  if cat=='wait' and not in_wait:in_wait=True;site=last_cpu;blits[site]+=indraw
  if cat=='cpu':
   if in_wait:in_wait=False
   c=canon(pc)
   # Library jump-table slots in Chip memory and the native wrapper are transparent.
   if not (c==pc and pc<0x200000) and not 0x2a130<=c<0x2a140:
    last_cpu='%06x'%c if pc<probe or pc>probe+0x40000 else 'fine:%x'%(pc-probe)
  if indraw:
   per[cur][cat]+=cost
   if in_wait or (cat=='irq' and in_wait):sites[site][cat]+=cost
  if depth and op(pc)==0x4e73:depth-=1
  if indraw and pc==end:
   complete+=1
   for k,v in per.items():accepted_per[k].update(v)
   for k,v in sites.items():accepted_sites[k].update(v)
   accepted_blits.update(blits);indraw=False
per=accepted_per;sites=accepted_sites;blits=accepted_blits;draws=complete
assert draws==json.loads((p/'hi25-analysis.json').read_text())['complete_draws']
out={'trace':p.name,'complete_draws':draws,'note':'ms per complete draw; incomplete boundaries excluded; inclusive until next top-level call; beam wait split explicitly',
 'calls':{k:{c:round(v*cyc_ms/draws,3) for c,v in per[k].items()}|{'total':round(sum(per[k].values())*cyc_ms/draws,3)} for k in sorted(per,key=lambda k:-sum(per[k].values()))},
 'wait_sites':[{'site':k,'waits_per_draw':round(blits[k]/draws,1),'spin_ms':round(v['wait']*cyc_ms/draws,3),'irq_ms':round(v['irq']*cyc_ms/draws,3)} for k,v in sorted(sites.items(),key=lambda x:-sum(x[1].values()))[:30]]}
(p/'h8-calls.json').write_text(json.dumps(out,indent=1)+'\n')
for k,v in list(out['calls'].items())[:28]:print('%8.3f  %-28s %s'%(v['total'],k,{c:x for c,x in v.items() if c!='total'}))
print('-- wait sites')
for x in out['wait_sites'][:20]:print(x)
