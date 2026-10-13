#!/usr/bin/env python3
"""Whole-output native c2p comparisons across alternating buffers and invalidation."""
import argparse, hashlib, json, random, re, struct
from pathlib import Path
from cd32_runtime import ROOT
from c2p_check import CPU, BASE, SRC, STACK, STOP, reference, ck, u

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    a.output=a.output.resolve()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.parents:raise ValueError('new tmp output required')
    blob=(a.build/'payload.bin').read_bytes()
    meta=json.loads((a.build/'build.json').read_text())
    control=meta.get('flight_control',False)
    sym={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    rng=random.Random(11);results=[]
    for model in (2,4):
        c=CPU(blob,model)
        if meta.get('release'):c.write(BASE+0x17b8,bytes.fromhex('4e75')) # pacing tested separately
        c.write(BASE+0x1de4,struct.pack('>I',3));c.write(BASE+0x1e04,struct.pack('>I',1))
        c.write(BASE+sym['flight_history'],struct.pack('>I',0xa0000))
        if 'flight_reference' in sym:c.write(BASE+sym['flight_reference'],struct.pack('>I',0xc0000))
        c.write(0x30000-778,struct.pack('>I',0x3000));c.write(0x3000-402,bytes.fromhex('4e75'))
        source=bytearray(rng.randbytes(64000))
        # Two alternating surfaces, then replacement, smaller geometry, resume,
        # inactive same-height conversion, and allocation-failure fallback.
        for i in range(36):
            height=128 if i==27 else 166 if i==28 else 200
            active=int(i!=30);custom=0 if i==31 else 3
            dst=(0x50000,0x60000)[i%2] if i<24 else (0x60000,0x70000)[i%2]
            if i%5!=0 and i not in (4,6):
                for _ in range(40 if i%7 else 10000):source[rng.randrange(64000)]=rng.randrange(256)
            src=bytes(source[:320*height]);want=reference(src)
            # The original binary, independently executed, is the primary oracle.
            ref=CPU(blob,model);gold,_=ref.run({128:0x17f6,166:0x195e,200:0x1ac6}[height],src,height)
            assert gold==want;ref.close()
            c.write(SRC,src+b'\x5a'*64);c.write(STACK,struct.pack('>I',STOP))
            c.write(BASE+sym['timing_active'],struct.pack('>H',active));c.write(BASE+0x1de4,struct.pack('>I',custom))
            if i==34:c.write(BASE+sym['flight_history'],bytes.fromhex('ffffffff'))
            for r in range(1,17):c.reg(r,0x12340000+r)
            c.reg(1,SRC);c.reg(2,dst);c.reg(5,0x30000);c.reg(8,STACK);c.reg(9,320);c.reg(12,height)
            before=[c.reg(r) for r in range(1,17)];c.writes=[]
            err=u.uc_emu_start(c.h,BASE+0x178a,STOP,10000000,3000000)
            if err:raise RuntimeError((model,i,hex(c.reg(18)),[hex(c.reg(r)) for r in range(1,17)],u.uc_strerror(err)))
            assert c.reg(18)==STOP
            got=c.read(dst,len(src));assert got==gold,(model,i,next(j for j,(x,y) in enumerate(zip(got,gold)) if x!=y))
            assert c.read(SRC,len(src))==src
            after=[c.reg(r) for r in range(1,17)]
            assert before[:7]+before[8:]==after[:7]+after[8:] and after[7]==STACK+4
            allowed=[(dst,dst+len(src)),(0xa0000,0xa0000+128000),(STACK-1024,STACK)]
            allowed += [(BASE+sym[k],BASE+sym[k]+n) for k,n in (('flight_destinations',8),('flight_history_order',2),('flight_verified',4)) if k in sym]
            if 'flight_reference' in sym:allowed.append((0xc0000,0xc0000+64000))
            for addr,n in c.writes:
                assert any(lo<=addr and addr+n<=hi for lo,hi in allowed),hex(addr)
            results.append(dict(model=model,frame=i,height=height,identical=True,planar_stores=sum(dst<=x<dst+len(src) for x,n in c.writes)))
        c.close()
    negative=[]
    if 'flight_verified' in sym and not control:
        for model in (2,4):
            c=CPU(blob,model);src=bytes(range(256))*250;dst=0x60000
            for off,value in ((0x1de4,3),(0x1e04,1),(sym['flight_history'],0xa0000),(sym['flight_destinations'],dst),(0x121e,0x2000)):
                c.write(BASE+off,struct.pack('>I',value))
            c.write(BASE+sym['timing_active'],bytes.fromhex('0001'))
            c.write(BASE+sym['flight_reference'],struct.pack('>I',0xc0000))
            # Record 0, order 0 maps to physical history 1.
            c.write(0xa0000+64000,src);c.write(SRC,src+b'\0'*32)
            wrong=bytearray(reference(src));wrong[0]^=1;c.write(dst,bytes(wrong))
            c.write(0x2004,bytes.fromhex('70094ef900001000'))
            c.write(STACK,struct.pack('>I',STOP));c.reg(8,STACK);c.reg(1,SRC);c.reg(2,dst);c.reg(9,320);c.reg(12,200)
            ck(u.uc_emu_start(c.h,BASE+0x178a,STOP,10000000,3000000))
            assert c.reg(18)==STOP and c.reg(9)==9, 'live twin accepted wrong output'
            negative.append(dict(model=model,corrupted_output_rejected=True));c.close()
    # Repeated pictures must actually exercise zero-store reuse.
    if not control:assert any(r['planar_stores']==0 for r in results), 'unchanged-buffer case missing'
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(dict(sha256=hashlib.sha256(blob).hexdigest(),cases=results,negative_controls=negative),indent=2)+'\n')
    print(f'PASS: {len(results)} whole-output native comparisons on 020/040')
if __name__=='__main__':main()
