#!/usr/bin/env python3
"""Verify candidate state writers with read-only gdb write watchpoints.
Break at the candidate store first, then watch and step that instruction; this
also works if gdb chooses software watchpoints (avoids millions of remote steps).
  state_watch.py OUT/state
"""
import json
from pathlib import Path
import sys
from state_fields import command
m=json.loads((Path(sys.argv[1])/'metadata.json').read_text()); hb=m['code_base']; a4=m['a4']
writers={'distance':(-17238,0xb2a6),'speed':(-13282,0xa8e6),
         'clock':(-10146,0x5b90),'opponent_distance':(-13356,0xde3e)}
log=[]
for name,(off,pc) in writers.items():
    addr=a4+off
    log.append(f'{name}: -{abs(off)}(a4), duel:{pc:05x}')
    log.append(command(f'break *{hb+pc:#x}\ncontinue\ndelete'))
    log.append(command(f'watch -location *(int*){addr:#x}\nstepi\ninfo registers pc a4 sp\nx/1uw {addr:#x}\ndelete'))
(Path(sys.argv[1])/'watchpoints.txt').write_text('\n'.join(log)+'\n')
print('\n'.join(log))
