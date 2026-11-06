#!/usr/bin/env python3
"""Read Exec task identity/priority/stack from an ignored full-memory dump.
  task_state.py CODE.bin BASE
The primary process is the cached pointer at -17474(a4). Locate the named
Road Drawer task independently by its Exec node type and name pointer.
"""
import argparse
from pathlib import Path
from td2_report import regions

def main():
    p=argparse.ArgumentParser();p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));a=p.parse_args()
    b=Path(a.dump).read_bytes();rr={n:lo for lo,hi,n,o in regions(b,a.base)}
    a4=rr['duel-data']+0x7ffe
    def u32(addr):
        i=addr-a.base
        if not 0<=i<=len(b)-4: raise ValueError(f'address outside dump: {addr:#x}')
        return int.from_bytes(b[i:i+4],'big')
    def name_at(i):
        n=u32(a.base+i+10)-a.base
        return b[n:n+64].split(bytes([0]))[0] if 0<=n<len(b) else b''
    tasks={u32(a4-17474):'cached game process'}
    for i in range(0,len(b)-92,2):
        if b[i+8]==1 and name_at(i)==b'Road Drawer':tasks[a.base+i]='named drawing task'
    for addr,source in tasks.items():
        i=addr-a.base
        priority=int.from_bytes(b[i+9:i+10],'big',signed=True)
        stack=[u32(addr+n) for n in (54,58,62)]
        print(f'{source}: address={addr:#x}, name={name_at(i)!r}, type={b[i+8]}, priority={priority}, SP={stack[0]:#x}, bounds={stack[1]:#x}..{stack[2]:#x}')
    if len(tasks)<2:raise RuntimeError('Road Drawer task not found; do not infer its priority')
if __name__=='__main__':main()
