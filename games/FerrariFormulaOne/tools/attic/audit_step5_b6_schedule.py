from pathlib import Path
import sys,re,json,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];name=sys.argv[1];p=r/'tmp/step5'/name;result=json.loads((p/'result.json').read_text());listing=(Path(result['slave']).parent/'fine.list').read_text();symbol={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)};probe=struct.unpack_from('>I',(p/'end.bin').read_bytes(),0x654e8)[0]-symbol['barrier']
loops=[];cur=None;car=-1;helper_hits=[]
guards={probe+int(a,16) for a in re.findall(r'^00:([0-9A-F]{8}).*tst.w \$32fbc$',listing,re.M)};guard_costs=collections.Counter()
conversion={probe+a:n for n,a in symbol.items() if n in ('velocity_context','bridge_context','heading_context','steering_sample','wear_sample','fuel_sample','velocity_speed_context')}
contexts={probe+symbol[n]:n for n in ('velocity_context','bridge_context','heading_context','steering_context','wear_context','fuel_context','velocity_speed_context','velocity_array_context','velocity_speed_array')}
trace=barto.load(p/'detail.bin')
for field in trace.fields:
 for pc,cost,regs in trace.instructions(field):
  if pc in guards:guard_costs[cost]+=1
  if pc==0x65174:
   if cur is not None:loops.append(cur)
   cur={'cars':[],'pairs':0,'blits':0,'opponent_conversion':[],'context_lookups':[]};car=-1
  if cur is None:continue
  if pc==0x671bc:
   car=regs[0]&65535
   if car<8:cur['cars'].append(car)
  if pc==0x68e50:cur['pairs']+=1
  if pc==0x24ae0:cur['blits']+=1
  if pc in contexts:cur['context_lookups'].append(contexts[pc])
  if pc in conversion and 1<=car<=7:cur['opponent_conversion'].append(conversion[pc])
loops=loops[1:21]
fail=[]
for i,x in enumerate(loops):
 pulse=len(x['cars'])==8
 expected_cars=list(range(7,-1,-1)) if pulse else [0]
 if x['cars']!=expected_cars:fail.append((i,'cars',x))
 if x['pairs']!=(28 if pulse else 7) or x['blits'] or x['opponent_conversion'] or x['context_lookups']:fail.append((i,'work',x))
report=dict(name=name,updates=len(loops),pulse_updates=sum(len(x['cars'])==8 for x in loops),failures=fail,passed=not fail,loops=loops,current_car_tst_cycles=dict(guard_costs),mean_current_car_tst_cycles=sum(k*v for k,v in guard_costs.items())/sum(guard_costs.values()))
(p/'schedule-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(name,'passed',not fail,'pulses',report['pulse_updates'],'failures',fail[:2])
