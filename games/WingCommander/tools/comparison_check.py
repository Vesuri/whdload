#!/usr/bin/env python3
"""D4 complete-output comparison seam: byte boundaries and rejecting controls.

Executes the assembled converter on 020/040. This is correctness, not timing.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from cd32_runtime import ROOT
from c2p_check import CPU, BASE, SRC, STACK, STOP, reference, ck, u


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('--control',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run',type=Path,action='append',default=[],help='live snapshots from this exact fixture')
    p.add_argument('--layout',type=Path)
    a=p.parse_args()
    if a.run and not a.layout:p.error('--run requires --layout')
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        p.error('fresh output under tmp/ required')
    blob=(a.build/'payload.bin').read_bytes()
    old=(a.control/'payload.bin').read_bytes()
    listing=(a.build/'slave.lst').read_text()
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',listing,re.M)}
    original_symbols={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.control/'slave.lst').read_text(),re.M)}
    assert sy==original_symbols, 'control layout changed'
    cmps=[int(x,16) for x in re.findall(r'^00:([0-9A-F]{8}) B388\s+.*cmpm.l',listing,re.M)]
    cmps=[x for x in cmps if sy['flight_delta']<=x<sy['flight_history']]
    assert len(cmps)==8 and cmps==list(range(cmps[0],cmps[0]+32,4))
    start=cmps[0]-4;end=start+82
    assert len(blob)==len(old) and blob[:start]==old[:start] and blob[end:]==old[end:]
    assert blob[start+38:end]==bytes(44), 'unreachable padding changed'
    history=0xa0000;dst=0x60000
    source=bytes(range(256))*250
    packed=reference(source)
    cases=0;negatives=[]
    for model in (2,4):
        c=CPU(blob,model)
        def run(candidate,offset):
            c.write(BASE,candidate)
            changed=bytearray(source);changed[offset]^=0x81
            c.write(SRC,bytes(changed));c.write(history,source)
            c.write(dst-32,b'\xa5'*32+packed+b'\x5a'*32)
            c.write(STACK,struct.pack('>I',STOP))
            for reg in range(1,17):c.reg(reg,0x12340000+reg)
            c.reg(1,SRC);c.reg(2,dst);c.reg(3,history);c.reg(8,STACK);c.reg(16,1)
            saved=[c.reg(reg) for reg in (3,4,5,6,7,11,12,13,14,15,16)]
            c.writes=[]
            ck(u.uc_ctl(c.h,10|(1<<30)))
            ck(u.uc_emu_start(c.h,BASE+sy['flight_delta'],STOP,10000000,3000000))
            assert c.reg(18)==STOP and c.reg(8)==STACK+4
            assert saved==[c.reg(reg) for reg in (3,4,5,6,7,11,12,13,14,15,16)]
            assert c.read(SRC,64000)==bytes(changed)
            assert c.read(dst-32,32)==b'\xa5'*32 and c.read(dst+64000,32)==b'\x5a'*32
            for address,size in c.writes:
                assert any(lo<=address and address+size<=hi for lo,hi in ((dst,dst+64000),(history,history+64000),(STACK-1024,STACK))),hex(address)
            return c.read(dst,64000)==reference(bytes(changed)) and c.read(history,64000)==bytes(changed)
        # Every byte of first and last blocks, including all eight comparison
        # positions; a single changed bit cannot hide in another changed block.
        for block in (0,1999):
            for byte in range(32):
                assert run(blob,block*32+byte),(model,block,byte)
                cases+=1
        missing=bytearray(blob);missing[cmps[-1]:cmps[-1]+2]=bytes.fromhex('4e71')
        assert not run(bytes(missing),63999),'last longword omitted without rejection'
        negatives.append(dict(model=model,omitted_last_comparison_rejected=True))
        c.close()
    live=[]
    for run in a.run:
        meta=json.loads((run/'result.json').read_text())
        fixture=(a.build/'WingCommanderCD32.Slave').read_bytes()
        assert hashlib.sha256(fixture).hexdigest()==meta['fixture']['sha256']
        layout=json.loads(a.layout.read_text());slave=layout['slave']
        fast=(run/'fast.bin').read_bytes();chip=(run/'chip.bin').read_bytes()
        def read(at,size):
            data=fast[at-0x200000:at-0x200000+size] if at>=0x200000 else chip[at:at+size]
            assert len(data)==size
            return data
        def value(name,fmt):return struct.unpack('>'+fmt,read(slave+sy[name],struct.calcsize('>'+fmt)))
        history,=value('flight_history','I');order,=value('flight_history_order','H')
        dest=value('flight_destinations','II')
        assert 0x200000<=history<0xa00000-128000 and order in (0,1)
        assert len(set(dest))==2 and all(0<x<0x200000-64000 for x in dest)
        assert set(dest)==set(struct.unpack('>II',read(layout['hunks'][0]+0x331f8,8)))
        for index,plane in enumerate(dest):
            physical=(1-index)^order
            expected=reference(read(history+64000*physical,64000))
            observed=read(plane,64000)
            assert observed==expected,(run,index,'live planar/history mismatch')
            broken=bytearray(observed);broken[-1]^=1
            assert bytes(broken)!=expected,'corrupted live output accepted'
        live.append(dict(run=run.name,buffers=2,planar_bytes_checked=128000,
                         snapshot_sha256={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in ('fast.bin','chip.bin')}))
    result=dict(live=live,cases=cases,negative_controls=negatives,payload_sha256=hashlib.sha256(blob).hexdigest(),
                control_sha256=hashlib.sha256(old).hexdigest(),identical_layout=True,
                changed_hunk_region=[hex(start),hex(end)],padding_bytes=44,
                scope='complete planar output, source/history, register and write bounds; not timing')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
