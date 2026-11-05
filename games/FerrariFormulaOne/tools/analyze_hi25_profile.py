#!/usr/bin/env python3
# Hi25 high-end frame anatomy from a hi25-profile trace: per-draw stage costs,
# the beam wait, the loop outside drawing (simulation ticks vs scheduler idle),
# WaitBlit time, and chip-bus slot usage per field from the DMA records.
# Costs include memory/DMA stalls; they are not pure arithmetic costs.
from pathlib import Path
import sys,json,bisect,collections,statistics,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];probe=int(r['probe'],16);host=int(r['host'],16)
rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 if pc is None:return -1
 i=bisect.bisect_right(keys,pc)-1
 if i>=0 and pc<rows[i]['actual']+rows[i]['size']:return rows[i]['old']+pc-rows[i]['actual']
 return pc
labels=sorted((v,k) for k,v in sy.items());sk=[v for v,k in labels]
hlabels=sorted((v,k) for k,v in r['host_symbols'].items());hk=[v for v,k in hlabels]
def owner(pc):
 if pc is None:return 'STOP'
 if pc==0x7fffffff:return 'gap'
 if probe<=pc<probe+max(sk)+0x400:return 'fine:'+labels[bisect.bisect_right(sk,pc-probe)-1][1]
 if host<=pc<host+max(hk):return 'host:'+hlabels[bisect.bisect_right(hk,pc-host)-1][1]
 if pc>=0xf80000:return 'rom:%06x'%(pc&~0xff)
 c=canon(pc)
 return ('native:' if c!=pc else 'other:')+'%06x'%(c&~0xff)
# Native canonical routine ranges of interest (entry points from B8Draw calls).
WAITBLIT=(0x2a130,0x2a140)
points=[('setup/publish','B8Draw'),('road prep','B8_65722'),('beam wait','B8_65728'),('clear 6b050','B8_65734'),('6b950','B8_6573a'),('road','B8_65748'),('optional scene 69bb8','B8_65790'),('scene/cars/HUD','B8_657a6'),('final flag/clock/publish','B8_65d6e')]
marks={probe+sy[v]:k for k,v in points};end=probe+sy['B8Frames']-2;wait_end=probe+sy['B8_65734'];entry=probe+sy['B8Draw']
idle_owners={'fine:schedule_begin','fine:FF1TimeDue','fine:FF1TimeSnapshot'}
trace=barto.load(p/'detail.bin')
mem=bytearray((p/'start.bin').read_bytes());mem+=bytes(0x200000-len(mem))+(p/'start-fast.bin').read_bytes()
def op(pc):return struct.unpack_from('>H',mem,pc)[0] if pc is not None and pc+2<=len(mem) else 0
glues=set();at=0x200000
while True:
 at=mem.find(bytes.fromhex('514f40d7007c0700'),at)
 if at<0:break
 glues.add(at);at+=2
assert glues
host_wait=host+r['host_symbols']['gfx_WaitBlit'];host_wait_end=host_wait+0x3a
def category(pc,o,depth):
 if depth:return 'irq'
 if pc is None:return 'stop'
 if host_wait<=pc<host_wait_end:return 'waitblit'
 c=canon(pc)
 if WAITBLIT[0]<=c<WAITBLIT[1]:return 'waitblit'
 if o=='fine:B8_65728' or o=='fine:B8_6572e' or o=='fine:B8_65732':return 'beam'
 return 'cpu'
heads=[f.cycles for f in trace.fields];field_ms=1000/49.9204102;cyc_ms=field_ms/statistics.mean(heads)
tot=collections.Counter();draws=[];cur=None;stage=None;running=0;events=[];outside=collections.Counter();outside_owner=collections.Counter()
depth=0;pending=0;cats=collections.Counter()
field_rows=[]
for f in trace.fields:
 fstart=running;fc=collections.Counter()
 for pc,cost,regs in trace.instructions(f):
  # 040/060 cached-loop time arrives as a gap record; charge it to the next instruction.
  if pc==0x7fffffff:pending+=cost;continue
  cost+=pending;pending=0
  if pc in glues:depth+=1
  if pc==entry:
   cur={'start':running,'field':f.index,'line':313*(running-fstart)/f.cycles,'stages':collections.Counter(),'owners':collections.Counter(),'wait_blit':0,'cycles':0};events.append(('draw',running,f.index))
  if cur is not None and pc in marks:stage=marks[pc]
  if cur is not None and pc==wait_end and 'wait_end' not in cur:cur['wait_end']=running;cur['wait_end_line']=313*(running-fstart)/f.cycles;cur['wait_end_field']=f.index
  o=owner(pc);cat=category(pc,o,depth)
  if depth and op(pc)==0x4e73:depth-=1
  if cur is not None:
   cur.setdefault('cats',collections.Counter())[cat]+=cost
   cur['cycles']+=cost;cur['stages'][stage]+=cost;cur['owners'][o]+=cost
   c=canon(pc) if pc not in (None,0x7fffffff) else -1
   if WAITBLIT[0]<=c<WAITBLIT[1] or o.startswith('other:') and False:cur['wait_blit']+=cost
   k='draw'
  else:
   k='idle' if o in idle_owners else 'irq-outside' if cat=='irq' else 'outside'
   if not draws:k='pre-window'
   else:outside[k]+=cost;outside_owner[o]+=cost
  fc[k]+=cost;tot[k]+=cost;running+=cost
  if cur is not None and pc==end:
   cur['end']=running;cur['end_field']=f.index;cur['end_line']=313*(running-fstart)/f.cycles;draws.append(cur);cur=None;stage=None
 # Chip-bus slots in this field.
 types=collections.Counter();blit_lines=set()
 for at in range(0,len(f.dma),f.dma_size):
  typ=struct.unpack_from('<h',f.dma,at+29)[0];types[typ]+=1
 field_rows.append({'field':f.index,'cycles':f.cycles,'phase':dict(fc),'dma':{str(k):v for k,v in sorted(types.items())}})
ms=lambda c:c*cyc_ms
complete=[d for d in draws if 'wait_end' in d]
n=len(complete)
intervals=[ms(b[1]-a[1]) for a,b in zip(events,events[1:])]
stage_tot=sum((d['stages'] for d in complete),collections.Counter());own_tot=sum((d['owners'] for d in complete),collections.Counter())
post=[ms(d['end']-d['wait_end']) for d in complete]
# Time from one draw's wait end to the next draw's wait check is the quantity that must stay < 2 fields.
nxt=[]
for a,b in zip(complete,complete[1:]):nxt.append(ms(b.get('wait_end')-a['wait_end']))
NAMES={0:'free',1:'refresh',2:'cpu',3:'copper',4:'audio',5:'blitter',6:'bitplane',7:'sprite',8:'disk',9:'conflict'}
dma=collections.Counter()
for x in field_rows:
 for k,v in x['dma'].items():dma[NAMES.get(int(k),k)]+=v
slots=sum(dma.values())
out={'trace':p.name,'fields':len(trace.fields),'ms_per_field':field_ms,'cpu_mhz':1/cyc_ms/1000,'complete_draws':n,
 'phase_ms_per_field':{k:ms(v)/len(trace.fields) for k,v in tot.most_common()},
 'draws':[{'start_field':d['field'],'start_line':round(d['line']),'wait_end_line':round(d['wait_end_line']),'wait_end_field':d['wait_end_field'],'end_field':d['end_field'],'end_line':round(d['end_line']),'draw_ms':round(ms(d['cycles']),3),'after_wait_ms':round(ms(d['end']-d['wait_end']),3),'cats_ms':{k:round(ms(v),3) for k,v in d.get('cats',{}).items()},'stages_ms':{k:round(ms(v),3) for k,v in d['stages'].items()}} for d in complete],
 'mean_draw_ms':statistics.mean(ms(d['cycles']) for d in complete) if n else None,
 'mean_after_wait_ms':statistics.mean(post) if n else None,
 'wait_end_to_wait_end_ms':nxt,'draw_entry_intervals_ms':intervals,
 'stage_ms_per_draw':{k:ms(v)/n for k,v in stage_tot.most_common()},
 'draw_category_ms_per_draw':{k:ms(v)/n for k,v in sum((d.get('cats',collections.Counter()) for d in complete),collections.Counter()).most_common()},
 'waitblit_ms_per_draw':statistics.mean(ms(d['wait_blit']) for d in complete) if n else None,
 'top_draw_owners_ms_per_draw':{k:round(ms(v)/n,3) for k,v in own_tot.most_common(40)},
 'outside_ms_per_field':{k:ms(v)/len(trace.fields) for k,v in outside.items()},'outside_ms_between_draws':{k:ms(v)/max(1,len(complete)-1) for k,v in outside.items()},
 'top_outside_owners_ms_per_field':{k:round(ms(v)/len(trace.fields),3) for k,v in outside_owner.most_common(25)},
 'dma_slot_share':{k:round(v/slots,4) for k,v in dma.most_common()},'dma_slots_per_field':{k:round(v/len(field_rows)) for k,v in dma.most_common()},
 'field_rows':field_rows}
(p/'hi25-analysis.json').write_text(json.dumps(out,indent=1)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('field_rows','draws','top_draw_owners_ms_per_draw','top_outside_owners_ms_per_field')},indent=1))
for d in out['draws']:print(d)
print('top draw owners');[print('  %8.3f %s'%(v,k)) for k,v in list(out['top_draw_owners_ms_per_draw'].items())[:30]]
print('top outside owners');[print('  %8.3f %s'%(v,k)) for k,v in list(out['top_outside_owners_ms_per_field'].items())[:15]]
