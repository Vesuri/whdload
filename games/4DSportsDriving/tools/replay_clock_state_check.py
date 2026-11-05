#!/usr/bin/env python3
"""Compare a completed replay step against a saved live semantic fixture."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
from simulation_fixture import read_fixture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('source',type=Path);p.add_argument('--tick',type=int,default=155);p.add_argument('--source-anchor',action='store_true');a=p.parse_args();cap=a.capture.resolve();m=json.loads((cap/'anchor.json').read_text());at=m['game_base']+0xe7b4
r=command(f'gdb delete\ntbreak *{at:#x} if *(unsigned char *)($a4+0x45)==2 && *(unsigned short *)($a4-0x940)=={a.tick}\ncontinue\ninfo registers pc');print(r,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==at
f=cap/f'replay-equal-step-{a.tick}.bin';command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');b=f.read_bytes();aa=m['data_base']+0x7ffe-m['memory_base'];state=b[aa-0xa80:aa-0x620]+b[aa+0x228:aa+0x22e]
for marker,size in [(b'4DA4PHYS',128),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
 o=b.index(marker)+12;state+=b[o:o+size]
if a.source_anchor:
 sm=json.loads((a.source/'anchor.json').read_text());assert sm['simulation_tick']==a.tick
 sb=(a.source/'memory.bin').read_bytes();sa=sm['data_base']+0x7ffe-sm['memory_base']
 old=sb[sa-0xa80:sa-0x620]+sb[sa+0x228:sa+0x22e]
 for marker,size in [(b'4DA4PHYS',128),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  o=sb.index(marker)+12;old+=sb[o:o+size]
else:
 old=next(s for t,h,s in read_fixture(a.source) if t==a.tick and h==m['active_simulation_word'])
assert len(state)==len(old)==1486
diff=[i for i,(x,y) in enumerate(zip(state,old)) if x!=y]
result=dict(tick=a.tick,bytes_compared=1486,differing_offsets=diff,equal=not diff)
(cap/f'replay-clock-state-{a.tick}.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert not diff
