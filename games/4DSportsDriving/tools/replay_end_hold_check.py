#!/usr/bin/env python3
"""Compare final replay state at the native replay-control loop (not live frame entry)."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('source',type=Path);p.add_argument('--completion',action='store_true');a=p.parse_args();cap=a.capture.resolve();src=a.source.resolve()
m=json.loads((cap/'anchor.json').read_text());sm=json.loads((src/'anchor.json').read_text());tick=sm['simulation_tick'];offset=0xe7b4 if a.completion else 0x95b4;at=m['game_base']+offset
# 95B4 CMP.B #7,-11(A5), then a backward branch inside the replay controls.
r=command(f'gdb delete\ntbreak *{at:#x} if *(unsigned short *)($a4-0x940)=={tick} && *(unsigned char *)($a4+0x45)==2\ncontinue\ninfo registers pc');print(r,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==at
f=cap/'disk-replayed-memory.bin';command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');b=f.read_bytes();old=(src/'memory.bin').read_bytes();packet=(src/'A4000-io-test.rpl').read_bytes()
count=struct.unpack_from('>I',packet,20)[0];assert count==tick+1
restored=(cap/'disk-restored-memory.bin').read_bytes();aa=m['data_base']+0x7ffe-m['memory_base'];slot=1;comp=packet[54264+368*slot:54264+368*(slot+1)]
assert restored[aa-0xa80:aa-0x620]==packet[31864+1120*slot:31864+1120*(slot+1)]
assert restored[aa+0x228:aa+0x22e]==comp[2:8]
for marker,start,size in [(b'4DA4PHYS',8,128),(b'4DTSTATE',136,32),(b'4DAUXPHY',168,192),(b'4DCAM050',360,8)]:
 q=restored.index(marker)+12;assert restored[q:q+size]==comp[start:start+size]
ptr=struct.unpack_from('>I',restored,aa-0x1770)[0]-m['memory_base'];assert restored[ptr:ptr+count]==packet[1864:1864+count]
def state(blob,meta):
 x=meta['data_base']+0x7ffe-meta['memory_base'];result=blob[x-0xa80:x-0x620]+blob[x+0x228:x+0x22e]
 for marker,size in [(b'4DA4PHYS',128),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  q=blob.index(marker)+12;result+=blob[q:q+size]
 return result
x=state(b,m);y=state(old,sm);assert len(x)==len(y)==1486;diff=[i for i,(u,v) in enumerate(zip(x,y)) if u!=v]
i=b.index(b'4DRPLLOD');v,res,cnt,read,install,cursor=struct.unpack_from('>HH4I',b,i+8);assert v in (3,4) and (res,cnt,read,install,cursor)==(0,1,0,0,1500)
assert b[i+32:i+36]==b'LOD1' and b[i+36+61630:i+40+61630]==b'LOD2'
assert b[aa+0x45]==2 and struct.unpack_from('>H',b,aa-0x940)[0]==tick
result=dict(fresh_process=True,game_bases=[sm['game_base'],m['game_base']],restored_checkpoint=1500,reconstructed_tick=tick,anchor_code_offset=hex(offset),anchor='complete simulation step before UNLK' if a.completion else 'native replay-control loop, end hold',bytes_compared=len(x),differing_offsets=diff,equal=not diff,read_status=read,install_status=install,guards=True)
(cap/'replay-reload-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert not diff
