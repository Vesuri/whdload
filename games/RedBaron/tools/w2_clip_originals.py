import json,sys
from pathlib import Path
sys.path.insert(0,'tools')
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import clip_model
root=Path('tmp/prof/w2-g1-a500-0-r2');sim=json.loads((root/'entry.json').read_text())['entry']['sim'];rows=[]
# Bounds are unchanged in these fixed native-preference trace chunks. Read their
# relocated storage from the captured memory, then also check observed compares.
for name in ('steady-0','steady-1','bank'):
 memory=(root/name/'memory-c00000.bin').read_bytes();base=0xc00000
 def u32(at):return int.from_bytes(memory[at-base:at-base+4],'big')
 def u16(at):return int.from_bytes(memory[at-base:at-base+2],'big')
 bounds_at=u32(sim+0x39ed6)
 active=None;pass_index=0;t=barto.load(root/name/'trace.bin')
 for f in t.fields:
  for pc,cycles,regs in t.instructions(f):
   if pc==sim+0x39ecc:pass_index=0
   elif pc==sim+0x39df2:
    at=bounds_at+pass_index*4;pass_index+=1
    active=dict(coords={},lo=u16(at),hi=u16(at+2),n=regs[5],sp=regs[15])
   elif active and pc in (sim+0x39e2c,sim+0x39e04):
    idx=(regs[3] if pc==sim+0x39e2c else regs[2])&65535;active['coords'][idx]=regs[0]
   elif active and pc==sim+0x39eca:
    if active['sp']==regs[15] and (active['n']<=1 or len(active['coords'])==active['n']):
     row=dict(coords=[v for k,v in sorted(active['coords'].items())],lo=active['lo'],hi=active['hi'],output=regs[4]&65535)
     clip_model.check(**{k:v for k,v in row.items() if k!='output'},expected=row['output']);rows.append(row)
    active=None
out=Path('tmp/plan/geometry/clip-calls.json');out.write_text(json.dumps(rows)+'\n');print(len(rows),'original passes checked')
