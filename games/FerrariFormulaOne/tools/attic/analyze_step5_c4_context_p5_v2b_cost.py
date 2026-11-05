from pathlib import Path
import sys,json,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5/c4-context-p5-v2b-ab-a500-baseline-profile';j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16);listing=Path(j['slave']).with_name('fine.list').read_text();symbols={n:probe+int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
gates={symbols[n] for n in ['C4P5VelocityGate','C4P5PositionGate']};padding={pc+k for pc in gates for k in [4,6]};loops=[];row=None;t=barto.load(p/'detail.bin')
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==0x65174:
   if row is not None:loops.append(row)
   row={'calls':0,'padding_cycles':0}
  if row is not None:
   if pc in gates:row['calls']+=1
   if pc in padding:row['padding_cycles']+=cost
loops=loops[1:19];mean=sum(x['padding_cycles'] for x in loops)/len(loops)
a=json.loads((p/'audit.json').read_text())['mean_cycles'];b=json.loads((r/'tmp/step5/c4-context-p5-v2b-ab-a500-omitted-profile/audit.json').read_text())['mean_cycles']
out={'updates':len(loops),'mean_calls':sum(x['calls'] for x in loops)/len(loops),'control_padding_cycles':mean,'matched_baseline_cycles':a,'candidate_cycles':b,'matched_saving_cycles':a-b,'saving_after_removing_control_padding_cycles':a-b-mean,'scope':'The equal-width control replaces eight bytes with MULU + two NOPs. Subtract their actual trace costs before claiming a gain over the unpadded helper.'}
(r/'manifest/step5-c4-p5-v2b-cost.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
