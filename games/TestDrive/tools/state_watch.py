#!/usr/bin/env python3
"""Check a TD seed-map writer using a read-only breakpoint and watchpoint."""
import argparse,json
from pathlib import Path
from td import server
from harness import command
from state_report import VARIABLES
p=argparse.ArgumentParser(description=__doc__);p.add_argument('state');p.add_argument('--name',choices=VARIABLES,default='vbl');p.add_argument('--writer',type=lambda s:int(s,0),default=None);a=p.parse_args()
writers={'vbl':0x18ba,'sound_vbl':0x26b6,'blitter_calls':0xd46,'blitter_busy_loops':0xd54,'joystick_direction':0x18e8}
if a.writer is None:
    if a.name not in writers:p.error('supply --writer for this variable')
    a.writer=writers[a.name]
m=json.loads((Path(a.state)/'metadata.json').read_text());off,size=VARIABLES[a.name];addr=m['a4']+off
server.request('stop');log=[server.request(f"until {m['code_base']+a.writer:#x}")]
typ={2:'unsigned short',4:'unsigned int'}[size]
log.append(command(f'set $old_value = *({typ}*){addr:#x}'))
log.append(command(f'watch -location *({typ}*){addr:#x}\nstepi\ninfo registers pc a4 a1\nx/1wx {addr:#x}\ndelete'))
if a.name=='vbl':
    r=command(f'printf "VBL_INCREMENT_OK=%d\\n", (*({typ}*){addr:#x} == $old_value+1)');log.append(r)
    if 'VBL_INCREMENT_OK=1' not in r:raise RuntimeError(r)
(Path(a.state)/'watchpoints.txt').write_text('\n'.join(log));print('\n'.join(log))
