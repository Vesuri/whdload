from pathlib import Path
import json,struct,sys
import barto_mmap as bm
for name in sys.argv[1:]:
 p=Path('tmp/prof')/name;meta=json.loads((p/'metadata.json').read_text());budget=json.loads((p/'frame-budget.json').read_text());t=bm.load(p/'trace.bin');o=8+4*len(t.sections)+16
 for _ in range(3):o+=4+struct.unpack_from('<I',t.data,o)[0]
 clock,unit=struct.unpack_from('<II',t.data,o);total=sum(f.cycles for f in t.fields);attributed=0;swaps=0
 for f in t.fields:
  for pc,c,r in t.instructions(f):attributed+=c;swaps+=pc==meta['layout']['code_base']+0xb4
 seconds=total*unit/(clock*64);coverage=attributed/total
 assert len(t.fields)==500 and abs(seconds-500*142102/7093790)<1e-6
 assert .9999<=coverage<=1.0001 and swaps==budget['swaps']
 result=dict(passed=True,fields=len(t.fields),seconds=seconds,instruction_coverage=coverage,swaps=swaps,clock=clock,cycle_unit=unit)
 (p/'trace-check.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result,flush=True)
