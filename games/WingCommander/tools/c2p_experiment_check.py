#!/usr/bin/env python3
"""D5 equal-layout diagnostics and complete live planar/history oracle.

Native execution checks semantics only; elapsed costs come from frame_capture.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from cd32_runtime import ROOT
from c2p_check import CPU, BASE, SRC, STACK, STOP, reference, ck, u

ARMS=('control','block040','full-original','full030','full040')


def symbols(build):
    return {n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',
                                            (build/'slave.lst').read_text(),re.M)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix',required=True,type=Path,help='build prefix, e.g. tmp/d5')
    p.add_argument('--layout',required=True,type=Path)
    p.add_argument('--run',action='append',type=Path,default=[])
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        p.error('new output below tmp/ required')
    builds={arm:Path(str(a.prefix)+'-'+arm) for arm in ARMS}
    sy=symbols(builds['control']); base=(builds['control']/'payload.bin').read_bytes()
    # Local labels differ by algorithm. All shared global entry/data symbols stay put.
    shared={k:v for k,v in sy.items() if '.' not in k and k!='FLIGHT_CONTROL'}
    changes={}; hashes={}
    for arm,build in builds.items():
        meta=json.loads((build/'build.json').read_text())
        assert meta['verify_only'] and meta['c2p_experiment']==arm
        candidate_symbols=symbols(build)
        assert all(candidate_symbols.get(k)==v for k,v in shared.items())
        payload=(build/'payload.bin').read_bytes()
        assert len(payload)==len(base)
        delta=[i for i,(x,y) in enumerate(zip(base,payload)) if x!=y]
        allowed=((sy['flight_delta'],sy['flight_history']),
                 (sy['flight_kalms_block'],sy['flight_kalms_block']+720),
                 (sy['flight_render_work'],sy['flight_render_work_done']))
        assert all(any(lo<=i<hi for lo,hi in allowed) for i in delta)
        if arm=='block040':assert delta and all(allowed[1][0]<=i<allowed[1][1] for i in delta)
        if arm.startswith('full'):
            assert bytes.fromhex('7e00') in payload[sy['flight_render_work']:sy['flight_render_work_done']]
            target={'full-original':0x1ac6,'full030':sy['kalms_030_200'],'full040':sy['kalms_040_200']}[arm]
            calls=[i for i in range(sy['flight_delta'],sy['flight_history'],2)
                   if payload[i:i+2]==bytes.fromhex('6100') and
                   i+2+int.from_bytes(payload[i+2:i+4],'big',signed=True)==target]
            assert len(calls)==1, 'full converter not selected'
        changes[arm]=[hex(min(delta)),hex(max(delta)+1)] if delta else []
        hashes[arm]=hashlib.sha256((build/'WingCommanderCD32.Slave').read_bytes()).hexdigest()
    # Reject an omitted converter, on both ISA models. This also checks the
    # single-block API with the real 8000-byte plane stride and exact output.
    block=(builds['block040']/'payload.bin').read_bytes(); negatives=[]
    for model in (2,4):
        for sabotage in (False,True):
            c=CPU(block,model);src=bytes(range(32));dst=0x60000
            c.write(SRC,src+bytes(32));c.write(dst,bytes(64000))
            c.write(STACK,struct.pack('>I',STOP));c.reg(1,SRC);c.reg(2,dst);c.reg(8,STACK)
            if sabotage:c.write(BASE+sy['flight_kalms_block'],bytes.fromhex('4e75'))
            ck(u.uc_emu_start(c.h,BASE+sy['flight_kalms_block'],STOP,10000000,3000000))
            assert c.reg(18)==STOP
            want=reference(src)
            got=b''.join(c.read(dst+8000*i,4) for i in range(8))
            assert (got==want)!=sabotage
            c.close()
        negatives.append(dict(model=model,omitted_converter_rejected=True))
    layout=json.loads(a.layout.read_text());live=[]
    for run in a.run:
        meta=json.loads((run/'result.json').read_text())
        arm=next(k for k,v in hashes.items() if v==meta['fixture']['sha256'])
        fast=(run/'fast.bin').read_bytes();chip=(run/'chip.bin').read_bytes()
        def read(at,n):
            data=fast[at-0x200000:at-0x200000+n] if at>=0x200000 else chip[at:at+n]
            assert len(data)==n
            return data
        def value(name,fmt):
            return struct.unpack('>'+fmt,read(layout['slave']+sy[name],struct.calcsize('>'+fmt)))
        history,=value('flight_history','I');order,=value('flight_history_order','H')
        dest=value('flight_destinations','II')
        assert 0x200000<=history<0xa00000-128000 and order in (0,1)
        assert len(set(dest))==2 and all(0<x<0x200000-64000 for x in dest)
        assert set(dest)==set(struct.unpack('>II',read(layout['hunks'][0]+0x331f8,8)))
        for i,plane in enumerate(dest):
            want=reference(read(history+64000*((1-i)^order),64000))
            assert read(plane,64000)==want,(run,i,'live output mismatch')
        live.append(dict(run=run.name,arm=arm,planar_bytes_checked=128000,
                         snapshot_sha256={n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in ('fast.bin','chip.bin')}))
    a.output.write_text(json.dumps(dict(equal_layout=True,fixture_sha256=hashes,
        changed_hunk_ranges=changes,negative_controls=negatives,live=live),indent=2)+'\n')
    print(f'PASS: five equal-layout arms, two negative controls, {len(live)*2} live buffers')


if __name__=='__main__':main()
