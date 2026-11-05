#!/usr/bin/env python3
"""D3 exact native pixel-region twins; Unicorn is not a timing instrument."""
import argparse
import hashlib
import json
import random
import re
import struct
from pathlib import Path
from cd32_runtime import ROOT, BASE
from timing_audit_check import CPU

S = 0x180000
AREA = 0x120000
TABLE = 0x110000
DESC = 0x111000


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--run', type=Path, default=ROOT/'tmp/phase10-isolated-turn-ntsc')
    p.add_argument('--layout', type=Path, help='frame_capture layout; uses fast.bin instead of end-fast.bin')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if (ROOT/'tmp').resolve() not in a.output.resolve().parents or a.output.exists():
        raise ValueError('new tmp output required')
    memory = (a.run/('fast.bin' if a.layout else 'end-fast.bin')).read_bytes()
    meta = json.loads((a.layout if a.layout else a.run/'result.json').read_text())
    chip = (a.run/'chip.bin').read_bytes() if a.layout else None
    blob = (a.build/'payload.bin').read_bytes()
    sy = {n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$', (a.build/'slave.lst').read_text(), re.M)}
    counts = dict(retained_memory=0, clear_shapes=0, span_shapes=0, overlap=0, no_map=0)
    rng = random.Random(3)
    pixels = rng.randbytes(0x10000)
    for model in (2,4):
        c = CPU(memory,meta,model)
        r = CPU(memory,meta,model)
        if chip:
            c.write(0,chip);r.write(0,chip)
        c.write(S,blob)
        c.write(S+sy['timing_game'],struct.pack('>I',c.code))
        c.write(S+sy['render_selected'],struct.pack('>H',30))
        def active(v):c.write(S+sy['timing_active'],struct.pack('>H',v))
        def twin(name, native, args=b'', region=(AREA,len(pixels))):
            saved = {reg:0x12340000+reg for reg in (3,4,6,7,11,12,13,14,15,16)}
            r.run(native,args,registers=saved)
            c.run(S+sy[name]-c.code,args,registers=saved)
            assert c.read(*region)==r.read(*region), (model,name,counts)
            if chip and region[0]==BASE:
                assert c.read(0,0x110000)==r.read(0,0x110000), (name,'CHIP pixel regions')
            # Both call sites consume only callee-saved registers afterwards.
            for reg in (3,4,5,6,11,12,13,14,15,16)+( (7,) if name=='view_compose' else () ):
                assert c.reg(reg)==r.reg(reg), (name,'saved register',reg)
        # Actual split rows and 134-span cockpit map; compare every FAST byte.
        for name,native,args in [('view_clear',0x31cd6,struct.pack('>IH',c.data+0x9154,0)),('view_compose',0x2cf0a,b'')]:
            for enabled in (0,1):
                for selected in (0,30):
                    c.write(BASE,memory);r.write(BASE,memory);active(enabled)
                    c.write(S+sy['render_selected'],struct.pack('>H',selected))
                    if chip:
                        c.write(0,chip[:0x110000]);r.write(0,chip[:0x110000])
                    twin(name,native,args,(BASE,len(memory)))
                    counts['retained_memory']+=1
        for selected in (0,30):
            c.reset();r.reset();active(1)
            c.write(S+sy['render_selected'],struct.pack('>H',selected))
            for cpu in (c,r):
                cpu.write(AREA,pixels)
                cpu.data_value(0x6f2c,'I',0)
                cpu.data_value(0x6f3c,'I',0x1000000)
            twin('view_compose',0x2cf0a)
            counts['no_map']+=1
        # Row permutation and sentinels make over-clear/under-clear observable.
        for enabled in (0,1):
            for align in range(4):
                for left,right,top,bottom,col,bulk in ((0,319,0,9,0,0),(0,319,2,5,0,0),(1,318,1,7,0,0),(3,31,4,4,0,0),(0,319,2,5,0x5a,0),(0,319,0,9,0,3200)):
                    c.reset();r.reset();active(enabled)
                    for cpu in (c,r):
                        cpu.write(AREA,pixels)
                        cpu.write(TABLE,b''.join(struct.pack('>I',AREA+1024+((i*7)%10)*512+align) for i in range(10)))
                        cpu.write(DESC,struct.pack('>5I6H',TABLE,AREA+1024,0,bulk,0,320,200,left,top,right,bottom))
                    twin('view_clear',0x31cd6,struct.pack('>IBB',DESC,col,0))
                    counts['clear_shapes']+=1
        def record(src,dst,n):
            if n<4:return struct.pack('>hhhII',-20-2*n,0,0,src,dst)
            head=(-src)&3;tail=(src+n)&3
            return struct.pack('>hhhII',-2*head,-2*((n-head-tail)//4),-2*tail,src,dst)
        # Every width, all source alignments, destination alignments, successive
        # maps, short records and exact byte tails. No cached map to invalidate.
        for n in range(1,321):
            for align in range(4):
                c.reset();r.reset();active(1)
                src=AREA+1024+align;dst=AREA+32768+((n+align)%4)
                table=record(src,dst,n)+record(src+512,dst+512,max(1,n//2))+struct.pack('>hhhII',4,0,0,0,0)
                for cpu in (c,r):
                    cpu.write(AREA,pixels);cpu.write(TABLE,table)
                    cpu.data_value(0x6f2c,'I',1);cpu.data_value(0x6f3c,'I',TABLE)
                twin('view_compose',0x2cf0a)
                counts['span_shapes']+=1
        for delta in (-33,-4,-1,0,1,4,15,31,32,64):
            for n in (3,32,65,319):
                c.reset();r.reset();active(1)
                for cpu in (c,r):
                    cpu.write(AREA,pixels);cpu.write(TABLE,record(AREA+2048,AREA+2048+delta,n)+struct.pack('>hhhII',4,0,0,0,0))
                    cpu.data_value(0x6f2c,'I',1);cpu.data_value(0x6f3c,'I',TABLE)
                twin('view_compose',0x2cf0a)
                counts['overlap']+=1
        # Missing clears and a truncated span must both fail the pixel oracle.
        assert pixels != c.read(AREA,len(pixels)), 'span negative control not exercised'
        c.reset();r.reset();active(1)
        c.write(BASE,memory);r.write(BASE,memory)
        r.run(0x31cd6,struct.pack('>IH',r.data+0x9154,0))
        assert c.read(BASE,len(memory))!=r.read(BASE,len(memory)), 'blanket-clear bypass accepted'
        r.write(AREA,pixels);c.write(AREA,pixels)
        for cpu,length in ((c,63),(r,64)):
            cpu.write(TABLE,record(AREA+1024,AREA+32768,length)+struct.pack('>hhhII',4,0,0,0,0))
            cpu.data_value(0x6f2c,'I',1);cpu.data_value(0x6f3c,'I',TABLE)
        r.run(0x2cf0a);c.run(S+sy['view_compose']-c.code)
        assert c.read(AREA,len(pixels))!=r.read(AREA,len(pixels)), 'short span accepted'
        c.close();r.close()
    result=dict(counts=counts,negative_controls=['blanket clear bypass','truncated span'],payload_sha256=hashlib.sha256(blob).hexdigest(),memory_sha256=hashlib.sha256(memory).hexdigest(),chip_sha256=hashlib.sha256(chip).hexdigest() if chip else None,scope='exact native output and callee-saved registers, not timing')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
