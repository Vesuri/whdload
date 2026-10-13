#!/usr/bin/env python3
"""Check live B2 ownership, FAST/CHIP placement and copper setup assumptions."""
import argparse
import json
import struct
import re
from pathlib import Path
from frame_report import display_records
from cd32_runtime import ROOT


def check_owner(src,dst,front):
    assert 0x200000<=src<0xa00000,'chunky source is not FAST'
    assert 0<dst<0x200000 and dst%8==0,'planar target is not aligned CHIP'
    assert dst!=front,'conversion targets displayed front'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path);p.add_argument('--layout',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        raise ValueError('new tmp report required')
    checked=json.loads((a.run/'check.json').read_text());assert checked['passed']
    cfg=[int(x,16) for x in (a.run/'observer.cfg').read_text().split()]
    rows=[l.split() for l in (a.run/'events.txt').read_text().splitlines() if l and not l.startswith('#')]
    ledger=display_records(a.run/'displaystats.bin')
    front_by_clock={f+checked['offset']:plane for f,v,index,plane,copper in ledger}
    front=None;seen=0;source=set();dest=set();lines=[]
    for row in rows:
        pc=int(row[0],16)
        if pc==cfg[3]:
            clock=int(row[24])
            front=front_by_clock.get(clock)
            if front is not None:
                line=int(row[4]);assert 4<=line<=16;lines.append(line)
        elif pc==cfg[-1] and front is not None:
            src,dst=int(row[16],16),int(row[17],16)
            check_owner(src,dst,front)
            source.add(src);dest.add(dst);seen+=1
    assert seen>100 and len(dest)==2 and len(source)==1
    layout=json.loads(a.layout.read_text());fast=(a.run/'fast.bin').read_bytes();chip=(a.run/'chip.bin').read_bytes()
    def read(at,n):return fast[at-0x200000:at-0x200000+n] if at>=0x200000 else chip[at:at+n]
    def long(at):return struct.unpack('>I',read(at,4))[0]
    def word(at):return struct.unpack('>H',read(at,2))[0]
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    assert json.loads((a.build/'build.json').read_text())['sha256']==json.loads((a.run/'result.json').read_text())['fixture']['sha256']
    late=long(layout['slave']+sy['release_late'])
    lost=long(layout['slave']+sy['timing_input_overflows'])
    assert lost==0,'input history overflow'
    a4=layout['hunks'][1]+0x7ffe;gfx=long(a4-778);init=long(gfx+38)
    init_ops=list(struct.iter_unpack('>HH',read(init,256)))
    waits=[(i,x,y) for i,(x,y) in enumerate(init_ops) if x&1]
    # The pinned KickEmu 3.1 copinit initializes registers/sprites, waits at
    # line 12, then jumps to COP2. Restarting COP2 at 4..16 retains its setup.
    first=waits[0];assert first[1:]==(0x0c01,0xfffe) and first[0]<=100
    jump=next(i for i,(x,y) in enumerate(init_ops) if x==0x008a)
    assert jump>first[0]
    lists=[]
    for index in (0,1):
        header=long(a4-532+4*index);ptr=long(header+4);ops=[]
        for n in range(1024):
            x,y=struct.unpack('>HH',read(ptr+4*n,4));ops.append((x,y))
            if (x,y)==(0xffff,0xfffe):break
        else:raise AssertionError('unterminated copper list')
        regs={x:y for x,y in ops if not x&1}
        assert regs[0x1fc]==3
        plane=long(layout['hunks'][0]+0x331f8+4*index)
        assert plane in dest
        planes=[(regs[0xe0+i*4]<<16)|regs[0xe2+i*4] for i in range(8)]
        assert planes==[plane+8000*i for i in range(8)]
        top=regs[0x8e]>>8
        # Even charging four colour clocks per instruction, the setup is
        # complete before the earliest active display line, in PAL and NTSC.
        assert 16+len(ops)*4/227<top
        lists.append(dict(index=index,instructions=len(ops),top=top,fmode=regs[0x1fc],planes=8))
    # Confirm the placement and ownership assertions reject the actual failure
    # classes observed during development, not just malformed report files.
    for src,dst,front in ((0x24000,next(iter(dest)),0),(next(iter(source)),next(iter(dest)),next(iter(dest)))):
        try:check_owner(src,dst,front)
        except AssertionError:pass
        else:raise AssertionError('ownership negative control passed')
    result=dict(conversions_checked=seen,fast_sources=len(source),chip_buffers=len(dest),
                presentation_lines=dict(__import__('collections').Counter(lines)),copper_lists=lists,
                os_setup_moves_before_wait=first[0],late_deferrals=late,input_overflows=lost,passed=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
