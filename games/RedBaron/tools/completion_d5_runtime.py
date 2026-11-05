"""Resolve only the pointers needed by external D5 acceptance checks."""
import json,re,sys
from pathlib import Path
import route_status as r
out=Path(sys.argv[1]);sim=json.loads((out/'sim.json').read_text())['sim']
syms={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',line))}
r.command('stop');raw=r.command(f'gdb x/3hx {sim+0x21d28:#x}');v=[int(x,16) for x in re.findall(r'0x[0-9a-f]+',raw.split(':',1)[1])];assert v[0]==0x4eb9
base=((v[1]<<16)|v[2])-syms['time_loop_gate']
h3=int(r.command(f'gdb p/u *(unsigned int*){base+syms["time_loop_h3"]:#x}').split('=')[1])
(out/'runtime.json').write_text(json.dumps(dict(sim=sim,slave=base,h3=h3)))
