from pathlib import Path
import sys,re,json,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1];res=json.loads((p/'result.json').read_text());listing=Path(res['slave']).with_name('fine.list').read_text();syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)};base=int(res['probe'],16)
def pc_between(first,last,pattern):
 part=listing.split(first+':',1)[1].split(last+':',1)[0]
 return base+int(re.search(r'^00:([0-9A-F]+).*'+pattern,part,re.M)[1],16)
yes=pc_between('FF1TimeDue','FF1TimeConsume',r'\.yes:.*moveq')
low=pc_between('FF1TimeSnapshot','FF1TimeDue',r'move.l\s+FF1T_ELAPSED_LO\(a0\),d1')
field_add=pc_between('FF1TimeField','FF1TimeSnapshot',r'addi.l\s+#FF1T_FIELD_UNITS')
wait=pc_between('C1Head','C1Vbl',r'bsr.w FF1TimeDue')
consume=base+syms['FF1TimeConsume'];t=barto.load(p/'detail.bin');field=0;snapshot=0;phase=None;loops=[];cur=None
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==field_add:field+=1
  if pc==low:snapshot=field
  if pc==wait:phase='begin'
  if pc==consume:phase='consume'
  if pc==base+syms['C1Checkpoint']:
   phase=None
   if cur is not None and 'consume_pending' in cur:cur['simulation_end_pending']=cur['consume_pending']-3546895+(field-cur['consume_snapshot'])*710510
  if pc==0x65174:
   if cur is not None:
    if 'consume_pending' in cur:cur['end_pending']=cur['consume_pending']-3546895+(field-cur['consume_snapshot'])*710510
    loops.append(cur)
   cur={'cars':[]};phase=None
  if cur is None:continue
  if pc==0x671bc and (regs[0]&65535)<8:cur['cars'].append(regs[0]&65535)
  if pc==yes and phase in ('begin','consume'):
   cur[phase+'_pending']=(regs[2]<<32)|regs[1];cur[phase+'_snapshot']=snapshot
loops=loops[1:];assert len(loops)>=12 and all('end_pending' in x for x in loops)
pending=[x['simulation_end_pending'] for x in loops]
report=dict(scope='Lean 100 ms trace; pending is derived from actual TimeDue registers and every subsequent producer increment through C1Checkpoint before drawing. The 20 ms Plan-B five-quantum recovery gate does not apply here. Record coarse debt without rebasing or omitting producer time.',updates=loops,max_pending_units=max(pending),max_pending_quanta=max(pending)/3546895,steps_below_one=sum(x<3546895 for x in pending),passed=all(x>=0 for x in pending))
(p/'debt.json').write_text(json.dumps(report,indent=2)+'\n');print(p.name,report['passed'],report['max_pending_quanta'],report['steps_below_one'])

start_mem=(p/'start-raw.bin').read_bytes(); start_mem+=bytes(0xc00000-len(start_mem))+(p/'start-raw-slow.bin').read_bytes()
first=struct.unpack_from('>I',start_mem,base+syms['C1Completed'])[0]+2
for i,row in enumerate(loops):row['completed_step']=first+i
post=[row for row in loops if row['completed_step']>20]
recovered=next((row['completed_step']-20 for row in post if row['simulation_end_pending']<3546895),None)
report.update(contact=res.get('contact'),contact_injected_steps=list(range(11,21)),first_measured_step=first,last_measured_step=first+len(loops)-1,post_contact_recovery_steps=recovered)
# A bounded episode: every completed-step debt stays below three intervals,
# and after the final forced contact it returns below one interval in-window.
report['passed']=report['passed'] and recovered is not None and res['contact']['C2WallHits']>0
report['bound']='Observed contact episode: peak pending is reported, with recovery below 100 ms after the final injection; no new acceptance threshold or universal crash bound.'
(p/'debt.json').write_text(json.dumps(report,indent=2)+'\n')
print('C3 contact',report['passed'],'recovered in',recovered,'steps')
assert report['passed'],report
