#!/usr/bin/env python3
"""Follow fresh-process disk restore and native replay to an equal-tick state."""
import argparse,json,struct,re
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('source',type=Path);p.add_argument('--slot',type=int,default=1);p.add_argument('--init-tail',action='store_true');p.add_argument('--restore-only',action='store_true');p.add_argument('--tick',type=int,default=1555);p.add_argument('--packet',default='A4000-io-test.rpl');a=p.parse_args();cap=a.capture.resolve();source=a.source.resolve()
m=json.loads((cap/'anchor.json').read_text());sm=json.loads((source/'anchor.json').read_text());old=(source/'memory.bin').read_bytes();assert sm['simulation_tick']==a.tick, 'Source capture is not at requested comparison tick'
at=m['game_base']+(0xe514 if a.init_tail else 0xe5e0)
if a.init_tail:
 mb=(cap/'memory.bin').read_bytes();counter=m['memory_base']+mb.index(b'4DRPLMNU')+24;condition=f'*(unsigned int *){counter:#x}==1'
else:condition=f'*(unsigned short *)($a5-2)=={a.slot}'
r=command(f'gdb delete\ntbreak *{at:#x} if {condition}\ncontinue\ninfo registers pc');print(r,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==at

def dump(name):
 f=cap/name;command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');return f.read_bytes()
b=dump('disk-restored-memory.bin');aa=m['data_base']+0x7ffe-m['memory_base'];packet=(source/a.packet).read_bytes();native=packet[31864+1120*a.slot:31864+1120*(a.slot+1)];comp=packet[54264+368*a.slot:54264+368*(a.slot+1)]
assert b[aa-0xa80:aa-0x620]==native
input_ptr=struct.unpack_from('>I',b,aa-0x1770)[0]-m['memory_base'];count=struct.unpack_from('>I',packet,20)[0]
assert b[input_ptr:input_ptr+count]==packet[1864:1864+count], 'Recorded inputs changed during initialization'
assert b[aa+0x228:aa+0x22e]==comp[2:8]
pr=b.index(b'4DA4PHYS')+12;tm=b.index(b'4DTSTATE')+12
assert b[pr:pr+128]==comp[8:136] and b[tm:tm+32]==comp[136:168]
aux=b.index(b'4DAUXPHY')+12;assert b[aux:aux+192]==comp[168:360]
cam=b.index(b'4DCAM050')+12;assert b[cam:cam+8]==comp[360:368]
print(f'Restored checkpoint{1500*a.slot} exactly from disk',flush=True)
if a.restore_only: raise SystemExit(0)
at=m['game_base']+0xe5f8
r=command(f'gdb delete\ntbreak *{at:#x} if *(unsigned short *)($a4-0x940)=={a.tick} && *(unsigned char *)($a4+0x45)==2\ncontinue\ninfo registers pc');print(r,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==at
b=dump('disk-replayed-memory.bin')
def state(blob,meta):
 x=meta['data_base']+0x7ffe-meta['memory_base'];pr=blob.index(b'4DA4PHYS')+12;tm=blob.index(b'4DTSTATE')+12
 aux=blob.index(b'4DAUXPHY')+12
 return blob[x-0xa80:x-0x620]+blob[x+0x228:x+0x22e]+blob[pr:pr+128]+blob[tm:tm+32]+blob[aux:aux+192]+blob[blob.index(b'4DCAM050')+12:blob.index(b'4DCAM050')+20]
x=state(b,m);y=state(old,sm);diff=[i for i,(u,v) in enumerate(zip(x,y)) if u!=v]
i=b.index(b'4DRPLLOD');version,reserved,count,read,install,cursor=struct.unpack_from('>HH4I',b,i+8)
assert (reserved,count,read,install,cursor)==(0,1,0,0,1500*a.slot)
extra=4 if version>=2 else 0
if version==2: assert struct.unpack_from('>I',b,i+28)[0]==1
assert b[i+28+extra:i+32+extra]==b'LOD1' and b[i+32+extra+61630:i+36+extra+61630]==b'LOD2'
result=dict(fresh_process=True,game_bases=[sm['game_base'],m['game_base']],restored_checkpoint=1500*a.slot,reconstructed_tick=a.tick,bytes_compared=len(x),differing_offsets=diff,equal=not diff,read_status=read,install_status=install,guards=True)
(cap/'replay-reload-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert not diff
