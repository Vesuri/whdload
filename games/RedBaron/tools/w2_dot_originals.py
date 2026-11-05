import json,sys
from pathlib import Path
sys.path.insert(0,'tools')
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import dot_model
root=Path('tmp/prof/w2-g1-a500-0-r2');sim=json.loads((root/'entry.json').read_text())['entry']['sim'];rows=[]
for name in ('steady-0','steady-1','bank'):
 active=None
 t=barto.load(root/name/'trace.bin')
 for f in t.fields:
  for pc,cycles,regs in t.instructions(f):
   if pc==sim+0x3b1fa:active=dict(v=[],n=[],sp=regs[15])
   elif active and pc==sim+0x38b24:
    active['v'].append(regs[1]);active['n'].append(regs[0]&65535)
   elif active and pc==sim+0x3b280:
    assert active.pop('sp')==regs[15] and len(active['v'])==3
    active['output']=regs[0];assert dot_model.original(active['v'],active['n'])==regs[0]
    rows.append(active);active=None
out=Path('tmp/plan/geometry/dot-calls.json');out.write_text(json.dumps(rows)+'\n');print(len(rows),'original calls extracted',flush=True)
