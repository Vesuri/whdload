#!/usr/bin/env python3
"""Save an ordinary SIM_RUNTIME state and resolve its live game/clock addresses."""
import sys,json,re,struct,hashlib
from pathlib import Path
from profile_window import command,ROOT
p=Path(sys.argv[1]).resolve();assert p.is_relative_to(ROOT/'tmp');p.mkdir(exist_ok=True)
slave=ROOT/'tmp/build/4DSportsDriving-runtime.slave';listing=slave.with_suffix('.lst')
command('stop');f=p/'memory.bin';command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');b=f.read_bytes()
s={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',listing.read_text(encoding='latin1'),re.M)}
o=b.index(b'4DSIMRUN');version,size,g,ready,failure=struct.unpack_from('>HHIII',b,o+8);assert (version,size,ready,failure)==(1,8,1,0)
assert 0x200000<g<0x600000
base=0x200000+o+12-s['sim_game'];data=4*struct.unpack_from('>I',b,g-0x200000-4)[0]+4
m=dict(memory_base=0x200000,slave_base=base,game_base=g,data_base=data,standalone_runtime=True)
(p/'anchor.json').write_text(json.dumps(m,indent=2)+'\n');(p/'slave.slave').write_bytes(slave.read_bytes());(p/'slave.lst').write_bytes(listing.read_bytes())
(ROOT/'tmp/runtime-input.json').write_text(json.dumps(dict(base=base,game=g,data=data,irq=base+s['sim_clock_interrupt']+10)))
aa=data+0x7ffe-0x200000
print(dict(selected=struct.unpack_from('>H',b,aa-0xbc)[0],active=struct.unpack_from('>H',b,aa-0x15fa)[0],mode=b[aa+0x45],detail=b[aa-0x7708],opponent=b[aa-0x174a],failure=failure))
