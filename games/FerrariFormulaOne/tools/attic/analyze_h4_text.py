from pathlib import Path
import sys,json,bisect,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];base=int(r['probe'],16);rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 if pc is None:return -1
 i=bisect.bisect_right(keys,pc)-1
 return rows[i]['old']+pc-rows[i]['actual'] if i>=0 and pc<rows[i]['actual']+rows[i]['size'] else pc
active=None;done=[];cost=0;draw=-1;clock=None;clocks=[]
trace=barto.load(p/'detail.bin')
for f in trace.fields:
 for pc,c,regs in trace.instructions(f):
  irq=(regs[16]>>8)&7
  if not irq:
   if pc==base+sy['B8Draw']:draw+=1
   if pc==base+sy['FF1PresentClock']:clock=dict(start=cost,blits=0,draw=draw)
   if clock is not None:
    if canon(pc)==0x24db4:clock['blits']+=1
    if pc==base+sy['FF1ClockCalendarDigits']-2:
     clock['ms']=(cost-clock.pop('start'))/14187.58;clocks.append(clock);clock=None
   if pc==base+sy['B8_65d56']:active=dict(start=cost,draw=draw,blits=0,glyphs=0,batched_entries=0)
   if active is not None:
    if canon(pc)==0x24db4:active['blits']+=1
    if canon(pc)==0x1aac0:active['glyphs']+=1
    if pc==base+sy['FF1RenderDemoText']:active['batched_entries']+=1
    if pc==base+sy['B8_65d5c']:
     active['ms']=(cost-active.pop('start'))/14187.58;done.append(active);active=None
  cost+=c
out=dict(status='passed',clock_calls=clocks,clock_mean_ms=sum(x['ms'] for x in clocks)/len(clocks),clock_blits_per_call=sorted(set(x['blits'] for x in clocks)),calls=done,mean_ms=sum(x['ms'] for x in done)/len(done),blits_per_call=sorted(set(x['blits'] for x in done)))
(p/'text-analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(p.name,out['mean_ms'],out['blits_per_call'])
