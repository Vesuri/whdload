#!/usr/bin/env python3
"""Queue one key in the ignored menu-probe slave's existing six-byte input slot."""
import argparse,re,struct,json
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('key',choices=['enter','tab','right','left','up','down','esc']);p.add_argument('shot');a=p.parse_args()
keys=dict(enter=0x440d,tab=0x4209,right=0x4e00,left=0x4f00,up=0x4c00,down=0x4d00,esc=0x451b)
lst=Path('tmp/build/RedBaron-menu-probe.slave.lst').read_text(encoding='latin1')
def symbol(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)$',lst,re.M)[1],16)
at=r.locate();base=at-symbol('tape_marker');state=r.read(at)
r.command(f'gdb dump binary memory tmp/build/probe-route.bin {base+symbol("tape_routeptr"):#x} {base+symbol("tape_routeptr")+4:#x}')
route=struct.unpack('>I',Path('tmp/build/probe-route.bin').read_bytes())[0]
commands=[f'set {{unsigned short}}{route:#x}=10',f'set {{unsigned short}}{route+2:#x}={keys[a.key]}',f'set {{unsigned short}}{route+4:#x}=0']
commands += [f'set {{unsigned short}}{base+symbol(n):#x}={v}' for n,v in [('tape_index',0),('tape_wait',0),('tape_hold',1)]]
print(r.command('gdb '+'\n'.join(commands)))
r.command(f'gdb dump binary memory tmp/build/probe-write-check.bin {route:#x} {route+6:#x}')
expected=struct.pack('>3H',10,keys[a.key],0)
if Path('tmp/build/probe-write-check.bin').read_bytes()!=expected:
    raise SystemExit('Debugger did not write the route. Use probe_menu.py to rebuild a fixed input tape.')
commands = [f'break *{state["emit_hook"]:#x}','continue','delete']
print(r.command('gdb '+'\n'.join(commands)));r.command('wait 3');r.command('stop');print(r.command('shot '+str(Path(a.shot).resolve())))
print(json.dumps(r.read(at)))
