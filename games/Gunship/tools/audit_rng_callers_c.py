"""Candidate direct RNG calls and effect-spawn callers in relocated 0658 hunks.
Aligned opcode scan, not control-flow reachability or an indirect-call proof.
"""
import json,struct,hashlib
from pathlib import Path
from amitools.binfmt.BinFmt import BinFmt
from amitools.binfmt.Relocate import Relocate
from layout import locate
root=Path(__file__).resolve().parents[1]
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
img=BinFmt().load_image(str(root/'tmp/game/Gunship/data/gamemule'))
data=Relocate(img).relocate(h)
targets={h[0]+off:name for off,name in [(0x7a5c,'rng_256'),(0x7a66,'rng_stack'),(0x7a6a,'rng_d1'),(0x9b9a,'spawn_effect')]}
refs=[]
for k,d in enumerate(data):
 for i in range(0,len(d)-1,2):
  op=int.from_bytes(d[i:i+2],'big');target=None
  if op in [0x4eb9,0x4ef9] and i+6<=len(d):target=int.from_bytes(d[i+2:i+6],'big')
  elif op in [0x6100,0x6000] and i+4<=len(d):target=h[k]+i+2+struct.unpack('>h',d[i+2:i+4])[0]
  elif op>>8 in [0x61,0x60] and op&255:target=h[k]+i+2+struct.unpack('b',d[i+1:i+2])[0]
  if target in targets:refs.append(dict(hunk=k,offset=f'{i:05x}',opcode=f'{op:04x}',target=targets[target]))
report=dict(hunk_sha256=[hashlib.sha256(d).hexdigest() for d in data],direct_candidates=refs,scope='aligned JSR/JMP absolute and BSR/BRA relative scan; data and indirect reachability require manual audit')
(root/'tmp/c/rng-callers.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(refs,indent=2))
