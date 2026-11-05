from pathlib import Path
import sys,json,re,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1]
j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16)
listing=(Path(j['slave']).parent/'fine.list').read_text()
sym={n:int(v,16)+probe for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
t=barto.load(p/'detail.bin');cycle=0;starts={};spans=collections.defaultdict(list);totals=collections.Counter();phase='other';draws=0;updates=0;last_frame=None
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==0x67120:
   starts['car_update']=cycle;phase='car_update';updates+=1
  if pc==0x65606 and 'car_update' in starts:
   spans['car_update'].append(cycle-starts.pop('car_update'));phase='other'
  if pc==sym['HeavyBegin']:
   starts['render']=cycle;phase='render';draws+=1
  if pc==sym['HeavyRestored']:
   if 'render' in starts:spans['render'].append(cycle-starts.pop('render'))
   if last_frame is not None:spans['presentation_interval'].append(cycle-last_frame)
   last_frame=cycle;phase='other'
  totals[phase]+=cost;cycle+=cost
clock=7093790
out={'scope':'Full loop with fixed crowded render poses. Car-update spans are native 67120 to 65606; render spans include fixture pose save/restore. Legacy buffer handover and tail remain in other. IRQ/gaps included in spans. Untraced FPS is authoritative.','trace':p.name,'cycles':cycle,'seconds':cycle/clock,'updates_started':updates,'draws_started':draws,'phase_cycles':dict(totals),'spans':{}}
for kind,values in spans.items():
 out['spans'][kind]={'count':len(values),'mean_ms':sum(values)/len(values)/clock*1000,'min_ms':min(values)/clock*1000,'max_ms':max(values)/clock*1000,'cycles':values}
(p/'heavy-fullloop.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
