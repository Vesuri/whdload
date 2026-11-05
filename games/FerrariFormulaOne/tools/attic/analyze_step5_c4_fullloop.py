#!/usr/bin/env python3
# Split every traced cycle of the drawing C4 candidate into scheduler phases:
# head/idle wait, simulation update, end bookkeeping, B8 drawing and the native
# loop glue. Interrupt-level cycles (SR IPL > 0) and STOP/gaps are kept apart.
from pathlib import Path
import sys,json,re,bisect,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/(sys.argv[1] if len(sys.argv)>1 else 'c4-fullloop-a500-candidate')
res=json.loads((p/'result.json').read_text());probe=int(res['probe'],16)
listing=(Path(res['slave']).parent/'fine.list').read_text()
syms=sorted((int(a,16),n) for n,a in re.findall(r'^([A-Za-z_][\w.]*)\s+00:([0-9A-F]{8})$',listing,re.M))
addrs=[a for a,_ in syms];sym={n:a for a,n in syms}
draw_call=int(re.search(r'^00:([0-9A-F]{8}) 6\w+\s+\d+:\s+bsr\.w B8Draw',listing,re.M)[1],16)
head=probe+sym['C1Head'];wait=head+0x2c;admit=head+0x34;leave=head+0x4e
end=probe+sym['C1End'];draw=probe+sym['B8Draw'];after_draw=probe+draw_call+4
clock=7093790
def owner(pc):
 if probe<=pc<probe+0x10000:return 'probe:'+syms[bisect.bisect_right(addrs,pc-probe)-1][1]
 if pc>=0xf80000:return 'ROM'
 return 'native:%05x'%(pc>>8<<8)
t=barto.load(p/'detail.bin')
phase='pre';tot=collections.Counter();by=collections.defaultdict(collections.Counter)
events=[];cyc=0;draws=0;updates=0;fields=0
for f in t.fields:
 fields+=1
 for pc,cost,regs in t.instructions(f):
  if pc==head:phase='head'
  elif pc==wait and phase=='head':phase='idle'
  elif pc==admit:phase='head'
  elif pc==leave:phase='leave'
  elif phase=='leave':phase='update';updates+=1;events.append(('update',cyc))
  elif pc==end:phase='end';events.append(('end',cyc))
  elif pc==draw and phase=='end':phase='draw';draws+=1;events.append(('draw',cyc))
  elif pc==after_draw and phase=='draw':phase='end';events.append(('drawn',cyc))
  cyc+=cost
  if phase=='pre':continue
  if pc is None:k='stopped'
  elif pc==0x7fffffff:k='gap'
  elif (regs[16]>>8)&7:k='irq'
  else:k='head' if phase=='leave' else phase
  tot[k]+=cost
  if pc not in (None,0x7fffffff):by[k][owner(pc)]+=cost
total=sum(tot.values());secs=total/clock
# Complete update and draw spans, from their markers.
spans=collections.defaultdict(list);open_={}
for e,c in events:
 if e=='update':open_['u']=c
 elif e=='end' and 'u' in open_:spans['update'].append(c-open_.pop('u'))
 elif e=='draw':open_['d']=c
 elif e=='drawn' and 'd' in open_:spans['draw'].append(c-open_.pop('d'))
out={'trace':p.name,'fields':fields,'seconds':secs,'updates_started':updates,'draws_started':draws,
 'phase_cycles':dict(tot.most_common()),'phase_percent':{k:round(100*v/total,2) for k,v in tot.most_common()},
 'update_ms':[round(c/clock*1000,2) for c in spans['update']],'draw_ms':[round(c/clock*1000,2) for c in spans['draw']],
 'top_owners':{k:{o:round(v/clock*1000/secs,2) for o,v in c.most_common(25)} for k,c in by.items()}}
(p/'fullloop.json').write_text(json.dumps(out,indent=1)+'\n')
print('%.3f s traced, %d updates, %d draws'%(secs,updates,draws))
for k,v in tot.most_common():print('%-8s %6.2f%%  %7.1f ms/s'%(k,100*v/total,v/clock*1000/secs))
for k in ('update','draw'):
 s=spans[k]
 if s:print(k,'complete spans',len(s),'mean %.2f ms (incl. IRQ)'%(sum(s)/len(s)/clock*1000),'min %.2f max %.2f'%(min(s)/clock*1000,max(s)/clock*1000))
for k in ('draw','irq','idle','end','head'):
 if k in by:print('--',k);[print('  %7.2f ms/s %s'%(v/clock*1000/secs,o)) for o,v in by[k].most_common(15)]
