from pathlib import Path
import sys,re,json,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1];res=json.loads((p/'result.json').read_text());listing=Path(res['slave']).with_suffix('.list').read_text();syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)};base=struct.unpack_from('>I',(p/'end.bin').read_bytes(),0x654e8)[0]-syms['barrier']
def pc_between(first,last,pattern):
 part=listing.split(first+':',1)[1].split(last+':',1)[0]
 return base+int(re.search(r'^00:([0-9A-F]+).*'+pattern,part,re.M)[1],16)
yes=pc_between('FF1TimeDue','FF1TimeConsume',r'\.yes:.*moveq')
low=pc_between('FF1TimeSnapshot','FF1TimeDue',r'move.l\s+FF1T_ELAPSED_LO\(a0\),d1')
field_add=pc_between('FF1TimeField','FF1TimeSnapshot',r'addi.l\s+#FF1T_FIELD_UNITS')
wait=pc_between('schedule_begin','schedule_end',r'bsr.w FF1TimeDue')
consume=base+syms['FF1TimeConsume'];t=barto.load(p/'detail.bin');field=0;snapshot=0;phase=None;loops=[];cur=None
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==field_add:field+=1
  if pc==low:snapshot=field
  if pc==wait:phase='begin'
  if pc==consume:phase='consume'
  if pc==base+syms['FF1PresentationAfterTick']:
   phase=None
   if cur is not None and 'consume_pending' in cur:cur['simulation_end_pending']=cur['consume_pending']-709379+(field-cur['consume_snapshot'])*710510
  if pc==0x65174:
   if cur is not None:
    if 'consume_pending' in cur:cur['end_pending']=cur['consume_pending']-709379+(field-cur['consume_snapshot'])*710510
    loops.append(cur)
   cur={'cars':[]};phase=None
  if cur is None:continue
  if pc==0x671bc and (regs[0]&65535)<8:cur['cars'].append(regs[0]&65535)
  if pc==yes and phase in ('begin','consume'):
   cur[phase+'_pending']=(regs[2]<<32)|regs[1];cur[phase+'_snapshot']=snapshot
loops=loops[1:21];assert len(loops)==20 and all('end_pending' in x for x in loops)
pulses=[]
for i,x in enumerate(loops):
 if len(x['cars'])!=8:continue
 recovery=next((j-i for j in range(i,min(i+5,len(loops))) if loops[j]['simulation_end_pending']<709379),None)
 pulses.append(dict(index=i,simulation_end_pending_units=x['simulation_end_pending'],next_loop_pending_units=x['end_pending'],quanta_to_below_one=recovery))
report=dict(scope='Lean instruction trace; no guest records. Pending snapshot from actual FF1TimeDue registers, corrected for every subsequent producer increment through the completed simulation at FF1PresentationAfterTick, before rendering. The next native loop boundary is retained separately; immediate drawing can add debt after simulation has already caught up. One quantum=709379 units. First installation interval dropped; same twenty complete updates as cycle report.',updates=loops,pulses=pulses,passed=bool(pulses) and all(x['quanta_to_below_one'] is not None for x in pulses))
(p/'debt.json').write_text(json.dumps(report,indent=2)+'\n');print(p.name,report['passed'],pulses)
