#!/usr/bin/env python3
"""Observe and dismiss the native replay error notice, then compare race state."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('reference',type=Path);a=p.parse_args();cap=a.capture.resolve();m=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes();lst=(cap/'slave.lst').read_text(encoding='latin1');s={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$',lst,re.M)};base=m['marker']+8-s['tape_game']
# Verified listing: the hold loop is28 bytes after the task's entry.
at=base+s['tape_replay_error_ack']+28
r=command(f'gdb delete\ntbreak *{at:#x} if $d2==50\ncontinue\ninfo registers pc');print(r,flush=True);assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==at
print(command('shot '+str(cap/'replay-error.png')),flush=True)
at=m['game_base']+0xe5f8
r=command(f'gdb delete\ntbreak *{at:#x} if *(unsigned short *)($a4-0x940)==160\ncontinue\ninfo registers pc');print(r,flush=True);assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==at
f=cap/'error-resumed-memory.bin';command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');b=f.read_bytes();i=b.index(b'4DRPLERR');v,res,count,status,before,after=struct.unpack_from('>HH4I',b,i+8);assert (v,res,count,status)==(1,0,1,1);assert before==after
rm=json.loads((a.reference/'anchor.json').read_text());rb=(a.reference/'memory.bin').read_bytes()
def state(blob,meta):
 x=meta['data_base']+0x7ffe-meta['memory_base'];pr=blob.index(b'4DA4PHYS')+12;tm=blob.index(b'4DTSTATE')+12
 aux=blob.index(b'4DAUXPHY')+12
 return blob[x-0xa80:x-0x620]+blob[x+0x228:x+0x22e]+blob[pr:pr+128]+blob[tm:tm+32]+blob[aux:aux+192]
x=state(b,m);y=state(rb,rm);diff=[i for i,(u,v) in enumerate(zip(x,y)) if u!=v]
r=dict(load_status=status,header_unchanged=True,bytes_compared=len(x),differing_offsets=diff,race_equal=not diff)
(cap/'replay-error-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert not diff
