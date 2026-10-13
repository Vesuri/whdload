#!/usr/bin/env python3
"""Native C1 target selection, wraparound, queue race and VBL deadline checks."""
import argparse
import ctypes as C
import json
import hashlib
import re
import struct
from pathlib import Path
from buffer_check import fixture, invoke, GAME, A4
from c2p_check import BASE, ck, u, P, I, Q
from cd32_runtime import ROOT


def check(blob,sy,game):
    count=0
    for model in (2,4):
        for hz in (50,60):
            for now,clock in ((100,100),(102,100),(0,0xffffffff),(0xffffffff,0xfffffffe)):
                for pending in (0,1):
                    for debt in range(0,hz,10):
                        c,_=fixture(blob,sy,game,model,[4])
                        for name,value in [('timing_hz',hz),('timing_clock',clock)]:c.write(BASE+sy[name],struct.pack('>I',value))
                        c.write(BASE+sy['timing_clock']+4,struct.pack('>I',debt))
                        c.write(A4-252,struct.pack('>I',now))
                        c.write(BASE+sy['release_pending'],struct.pack('>H',pending))
                        assert invoke(c,BASE+sy['release_predict'])
                        target=(now+1+pending)&0xffffffff
                        age=(target-clock)&0xffffffff
                        expected=min(hz+20,debt+age*10)
                        assert c.reg(15)==expected
                        assert c.read(BASE+sy['release_render_time'],16)==struct.pack('>4I',target,clock,debt,expected)
                        # Publication copies immutable prediction metadata; no early display.
                        c.write(BASE+sy['release_pending'],bytes(2))
                        c.write(BASE+sy['timing_data'],struct.pack('>I',A4-0x7ffe))
                        assert invoke(c,BASE+sy['release_publish'])
                        c.write(BASE+sy['release_render_time'],bytes(16))
                        c.write(A4-252,struct.pack('>I',(target-1)&0xffffffff))
                        assert invoke(c,BASE+sy['release_vblank'])
                        assert c.read(BASE+sy['release_pending'],2)==b'\0\1'
                        c.write(A4-252,struct.pack('>I',target))
                        assert invoke(c,BASE+sy['release_vblank'])
                        assert c.read(BASE+sy['release_pending'],2)==bytes(2)
                        c.close();count+=1
        # Force a field rollover between snapshot reads: must retry and use new field.
        c,_=fixture(blob,sy,game,model,[4]);c.write(BASE+sy['timing_hz'],struct.pack('>I',50))
        c.write(BASE+sy['timing_clock'],struct.pack('>II',100,0));reads=[]
        def hook(h,kind,address,size,value,data):
            c.write(A4-252,struct.pack('>I',100 if not reads else 101));reads.append(1)
        callback=C.CFUNCTYPE(None,P,I,Q,I,C.c_int64,P)(hook);handle=C.c_size_t()
        ck(u.uc_hook_add(c.h,C.byref(handle),1<<10,callback,None,A4-252,A4-249))
        assert invoke(c,BASE+sy['release_predict']) and len(reads)>=4
        assert c.read(BASE+sy['release_render_time'],4)==struct.pack('>I',102)
        c.close()
    return count


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        p.error('choose a new output below tmp/')
    blob=(a.build/'payload.bin').read_bytes();sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    original=(ROOT/'tmp/originals/cd32/WingCommanderCD32/data/wing.english').read_bytes()
    assert hashlib.sha256(original).hexdigest()=='093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657'
    game=original[44:44+0x35ea4]
    count=check(blob,sy,game)
    broken=bytearray(blob);broken[sy['release_predict']:sy['release_predict']+2]=bytes.fromhex('4e75')
    try:check(bytes(broken),sy,game)
    except AssertionError:pass
    else:raise AssertionError('disabled prediction negative control passed')
    result=dict(cases=count,race_cases=2,negative_controls=['disabled-prediction'],passed=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(result)

if __name__=='__main__':main()
