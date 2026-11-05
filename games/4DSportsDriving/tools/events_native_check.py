#!/usr/bin/env python3
"""Read installed event-hook results at original native continuations."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--case',type=int,choices=range(1,7),required=True);a=p.parse_args();cap=a.capture.resolve();m=json.loads((cap/'anchor.json').read_text());off={1:0x11686,2:0x20df0,3:0x5988,4:0xe85c,5:0x5988,6:0x5988}[a.case];at=m['game_base']+off
fixture_a5=m['memory_base']+(cap/'memory.bin').read_bytes().index(b'4DEVNTFX')+16
out=command(f'gdb delete\ntbreak *{at:#x} if $a5=={fixture_a5:#x}\ncontinue\ninfo registers pc');print(out,flush=True);assert int(re.search(r'^pc\s+0x([0-9a-f]+)',out,re.M)[1],16)==at
path=cap/'event-memory.bin';command(f'gdb dump binary memory {path.relative_to(ROOT)} 0x200000 0x600000');b=path.read_bytes();a4=m['data_base']+0x7ffe-m['memory_base'];buf=b.index(b'4DEVNTFX')+8;time=b.index(b'4DTSTATE')+12
result={'case':a.case,'native_return_offset':hex(off)}
if a.case==1:
 absolute=struct.unpack_from('>I',b,time+16)[0];local=struct.unpack_from('>H',b,a4-0x93a)[0];assert (absolute,local)==(73499,29999);result.update(absolute_event=absolute,native_local=local)
if a.case==2:
 local=struct.unpack_from('>H',b,buf+6)[0];current=struct.unpack_from('>H',b,a4-0x940)[0];assert (local,current-local)==(28499,10);result.update(rebased_local=local,elapsed_ticks=current-local)
if a.case==3:
 average=struct.unpack_from('>H',b,buf+4)[0];assert average==125;result.update(average=average,denominator=65536)
if a.case==4:
 total=struct.unpack_from('>Q',b,time+24)[0];low=struct.unpack_from('>I',b,a4-0x944)[0];assert (total,low)==(4294967296,0);result.update(total=total,native_low=low)
if a.case in (5,6):
 average=struct.unpack_from('>H',b,buf+4)[0];expected={5:255,6:111}[a.case];assert average==expected,(average,expected);result.update(average=average,denominator=75000)
assert b[buf+15]==0x5a;result['guard_intact']=True;(cap/'event-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
