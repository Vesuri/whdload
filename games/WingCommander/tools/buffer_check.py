#!/usr/bin/env python3
"""Native two-buffer queue/VBL/reuse contract against the original publisher."""
import argparse
import ctypes as C
import hashlib
import json
import re
import struct
from pathlib import Path
from c2p_check import CPU, BASE, STACK, STOP, ck, u, P, I, Q
from cd32_runtime import ROOT

GAME=0x200000
A4=0x40000

def invoke(c, address, limit=10000):
    c.write(STACK,struct.pack('>I',STOP));c.reg(8,STACK)
    ck(u.uc_emu_start(c.h,address,STOP,1000000,limit))
    return c.reg(18)==STOP


def fixture(blob,sy,game,model,samples):
    c=CPU(blob,model)
    ck(u.uc_mem_map(c.h,GAME,0x40000,7))
    ck(u.uc_mem_map(c.h,0xdff000,4096,7))
    c.write(GAME,game)
    c.write(BASE+sy['timing_game'],struct.pack('>I',GAME))
    c.write(BASE+sy['release_publish_resume'],struct.pack('>I',GAME+0x33796))
    c.write(BASE+sy['release_teardown_resume'],struct.pack('>I',GAME+0x337f0))
    c.write(BASE+sy['timing_active'],struct.pack('>H',1))
    c.write(A4-752,struct.pack('>h',-1))
    c.write(A4-778,struct.pack('>I',0x5000))
    c.write(A4-532,struct.pack('>II',0x7000,0x7020))
    c.write(0x7004,struct.pack('>I',0x8000))
    c.write(0x7024,struct.pack('>I',0x9000))
    c.write(GAME+0x331f8,struct.pack('>II',0x60000,0x70000))
    for r in range(1,17):c.reg(r,0x12340000+r)
    c.reg(5,A4);c.reg(17,0x2715)
    reads=[]
    def hook(h,kind,address,size,value,data):
        if address==0xdff004:
            v=samples[min(len(reads),len(samples)-1)]
            c.write(address,struct.pack('>I',v<<8));reads.append(v)
    c.beam_hook=C.CFUNCTYPE(None,P,I,Q,I,C.c_int64,P)(hook)
    handle=C.c_size_t()
    ck(u.uc_hook_add(c.h,C.byref(handle),1<<10,c.beam_hook,None,0xdff004,0xdff007))
    return c,reads


def exercise(blob,sy,game):
    results=[]
    for model in (2,4):
        for samples,late in (([4],False),([0,256,4,4],False),([32],True),([300],True),([4,4,30,30],True)):
            c,reads=fixture(blob,sy,game,model,samples)
            c.write(GAME+0x33210,struct.pack('>H',1))
            assert invoke(c,BASE+sy['release_publish'])
            assert c.read(BASE+sy['release_pending'],2)==b'\0\1'
            assert c.read(BASE+sy['release_pending_plane'],4)==struct.pack('>I',0x70000)
            assert not any(a in (0xdff084,0xdff08a) for a,n in c.writes),'main thread touched copper'
            assert not invoke(c,BASE+sy['release_buffer_wait'],100),'pending buffer reused'
            before=[c.reg(r) for r in range(1,18)]
            c.writes=[]
            assert invoke(c,BASE+sy['release_vblank'])
            after=[c.reg(r) for r in range(1,18)]
            assert before[:7]+before[8:]==after[:7]+after[8:],'IRQ register/CCR corruption'
            pending=int.from_bytes(c.read(BASE+sy['release_pending'],2),'big')
            jumps=[i for i,(a,n) in enumerate(c.writes) if a==0xdff08a]
            assert pending==int(late)
            assert bool(jumps)==(not late)
            if not late:
                copper=[i for i,(a,n) in enumerate(c.writes) if a==0xdff084]
                retired=[i for i,(a,n) in enumerate(c.writes) if a==BASE+sy['release_pending']]
                assert len(copper)==len(jumps)==len(retired)==1 and copper[0]<jumps[0]<retired[0]
                assert c.read(0xdff084,4)==struct.pack('>I',0x9000)
                assert c.read(BASE+sy['release_front'],4)==struct.pack('>I',0x70000)
                assert invoke(c,BASE+sy['release_buffer_wait'])
            else:
                assert c.read(BASE+sy['release_late'],4)==struct.pack('>I',1)
                assert not invoke(c,BASE+sy['release_buffer_wait'],100)
                # The same pending picture must be retried, even after leaving flight.
                samples[:]=[4]
                c.write(BASE+sy['timing_active'],b'\0\0')
                assert invoke(c,BASE+sy['release_vblank'])
                assert c.read(BASE+sy['release_pending'],2)==b'\0\0'
                assert invoke(c,BASE+sy['release_buffer_wait'])
            # A consumed request cannot be displayed again by another callback.
            c.writes=[];assert invoke(c,BASE+sy['release_vblank'])
            assert not any(a==0xdff08a for a,n in c.writes)
            results.append(dict(model=model,initial_beams=reads[:4],late_deferred=late));c.close()
        # Native publication lock defers the request without touching its list.
        c,_=fixture(blob,sy,game,model,[4]);c.write(A4-752,b'\0\0')
        assert invoke(c,BASE+sy['release_publish']);c.writes=[]
        assert invoke(c,BASE+sy['release_vblank'])
        assert c.read(BASE+sy['release_pending'],2)==b'\0\1'
        assert not any(a in (0xdff084,0xdff08a) for a,n in c.writes);c.close()
        # Teardown drains the request, then preserves the native inactive path.
        c,_=fixture(blob,sy,game,model,[4])
        assert invoke(c,BASE+sy['release_publish'])
        assert not invoke(c,BASE+sy['release_teardown'],100)
        assert invoke(c,BASE+sy['release_vblank'])
        assert invoke(c,BASE+sy['release_teardown'])
        assert c.read(BASE+sy['release_front'],4)==bytes(4)
        c.close()
        a,_=fixture(blob,sy,game,model,[4]);b,_=fixture(blob,sy,game,model,[4])
        assert invoke(a,BASE+sy['release_teardown']) and invoke(b,GAME+0x337ea)
        assert [a.reg(r) for r in range(1,18)]==[b.reg(r) for r in range(1,18)]
        assert a.read(GAME+0x331f4,0x420)==b.read(GAME+0x331f4,0x420)
        a.close();b.close()
        # Inactive publication must match the original routine's effects/live-out.
        for index in (0,1):
            a,_=fixture(blob,sy,game,model,[4]);b,_=fixture(blob,sy,game,model,[4])
            for c in (a,b):
                c.write(BASE+sy['timing_active'],b'\0\0')
                c.write(GAME+0x33210,struct.pack('>H',index))
            assert invoke(a,BASE+sy['release_publish']) and invoke(b,GAME+0x3378e)
            assert [a.reg(r) for r in range(1,18)]==[b.reg(r) for r in range(1,18)]
            for start,size in ((A4-800,800),(0x5000,0x100),(0xdff000,0x100)):
                assert a.read(start,size)==b.read(start,size)
            a.close();b.close()
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:raise ValueError('new tmp report required')
    blob=(a.build/'payload.bin').read_bytes()
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    raw=(ROOT/'tmp/game/WingCommanderCD32/data/wing.english').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657'
    game=raw[44:44+0x35ea4]
    results=exercise(blob,sy,game)
    negatives=[]
    for name,label,patch in (('reuse-before-ack','release_buffer_wait',bytes.fromhex('4e75')),
                             ('no-copper-restart','release_presented',None)):
        broken=bytearray(blob)
        if patch:broken[sy[label]:sy[label]+len(patch)]=patch
        else:
            at=sy[label]-6
            assert broken[at:at+2]==bytes.fromhex('33c0')
            broken[at:at+6]=bytes.fromhex('4e714e714e71')
        try:exercise(bytes(broken),sy,game)
        except AssertionError:negatives.append(name)
        else:raise AssertionError('negative control passed: '+name)
    a.output.write_text(json.dumps(dict(cases=results,original_publication_cases=4,locked_cases=2,negative_controls=negatives),indent=2)+'\n')
    print('PASS: buffer queue/retire, late IRQ, lock, original publication and negative controls')

if __name__=='__main__':main()
