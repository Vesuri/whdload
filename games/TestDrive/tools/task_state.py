#!/usr/bin/env python3
"""Inspect TD's cached CLI process and independently locate the Road Drawer Exec task."""
import argparse,json
from pathlib import Path
from td_report import regions

def inspect(dump,base,chip=None):
    b=Path(dump).read_bytes();c=Path(chip).read_bytes() if chip else b''
    rr={n:lo for lo,hi,n,o in regions(b,base)};a4=rr['td-data']+0x7ffe
    def read(addr,n):
        if base<=addr and addr+n<=base+len(b):return b[addr-base:addr-base+n]
        if 0<=addr and addr+n<=len(c):return c[addr:addr+n]
        raise ValueError(f'address outside dumps: {addr:#x}')
    def u32(addr):return int.from_bytes(read(addr,4),'big')
    def name(addr):
        p=u32(addr+10);s=bytearray()
        for i in range(64):
            v=read(p+i,1)
            if v==b'\0':return s.decode('latin1')
            s.extend(v)
        raise ValueError('unterminated task name')
    tasks={u32(a4-22432):'cached game process (FindTask(NULL))'}
    for start,mem in [(base,b),(0,c)]:
        for i in range(0,len(mem)-92,2):
            if mem[i+8]!=1:continue
            try:
                if name(start+i)=='Road Drawer':tasks[start+i]='named drawing task'
            except ValueError:pass
    result=[]
    for addr,source in tasks.items():
        sp,lo,hi=[u32(addr+n) for n in (54,58,62)]
        typ=read(addr+8,1)[0]
        if typ not in (1,13) or not lo<hi or hi-lo>0x100000:raise ValueError('invalid Exec task/stack')
        result.append(dict(source=source,name=name(addr),type=typ,priority=int.from_bytes(read(addr+9,1),'big',signed=True),address=hex(addr),sp=hex(sp),lower=hex(lo),upper=hex(hi),saved_sp_in_bounds=lo<=sp<=hi))
    if len(result)<2:raise RuntimeError('Road Drawer task not found yet')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('--chip');a=p.parse_args();print(json.dumps(inspect(a.dump,a.base,a.chip),indent=2))
