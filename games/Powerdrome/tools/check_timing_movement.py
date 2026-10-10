#!/usr/bin/env python3
"""Audit native movement arithmetic from read-only before/after probes.

Summed movement intervals are diagnostics, not elapsed-time equivalence or lap distance.
"""
import argparse
import json
from pathlib import Path
import re
import struct


def signed16(n):return ((n&65535)^32768)-32768

def trunc_div(n,d):return (abs(n)//d)*(-1 if n<0 else 1)

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
a=p.parse_args()
for root in a.captures:
    log=(root/'swaps-gdb.txt').read_text()
    start=scalar=vector=None;rows=[];modified=[]
    for field,offset,values in re.findall(r'^PDMOVE_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',log,re.M):
        field=int(field);off=int(offset,16);v=list(map(int,values.split()))
        assert len(v)==14
        if off==0xccee:
            assert start is None, 'Previous movement never completed'
            start=(field,v)
        elif off==0xcd2c:
            assert start and scalar is None
            scalar=v
            nominal=trunc_div(signed16(v[1])*signed16(v[0]),24)
            if signed16(v[2])!=nominal:modified.append((field,nominal,signed16(v[2])))
        elif off==0xcd3a:
            assert scalar and vector is None
            vector=v
            expected=[(signed16(scalar[i])*signed16(scalar[2])>>12)&65535 for i in (3,4,5)]
            assert v[3:6]==expected, (root.name,field,'direction multiplication',v[3:6],expected)
        elif off==0xcde2:
            assert start and scalar and vector
            assert v[6:9]==start[1][9:12], 'Saved previous position differs from movement input'
            # Constraint/fall/impulse paths may modify these vectors after cd3a.
            displacement=[signed16(v[i+9]-v[i+6]) for i in range(3)]
            rows.append((start[0],field,scalar[0],scalar[1],signed16(scalar[2]),displacement))
            start=scalar=vector=None
    assert len(rows)>=20
    assert all(4<=r[2]<=50 for r in rows), 'Movement interval outside experimental clamp'
    incidents=[(int(f),off) for f,off in re.findall(r'^PDEVENT (-?\d+) (0x(?:fc9e|fcea|fec6))$',log,re.M)]
    before=[r for r in rows if not incidents or r[1]<incidents[0][0]]
    print(f'{root.name}: {len(rows)} complete vector multiplications and saved positions verified; {len(modified)} wind/other scalar adjustments')
    print(f'  Before first incident: {len(before)} movements, {sum(r[2] for r in before)*5} ms of applied intervals; incident probes {incidents}')
    if modified:print(f'  First scalar adjustments (field, nominal, actual): {modified[:3]}')

    diagnostics=[list(map(int,v.split())) for v in re.findall(r'^PDMCLK_EVENT (.+)$',log,re.M)]
    if diagnostics:
        data=(root/'code.bin').read_bytes()
        blocks=[m.start() for m in re.finditer(b'PDMCLK0[12]',data)
                if struct.unpack_from('>H',data,m.start()+8)[0]==1]
        assert len(blocks)==1
        previous,raw,applied,steps,clipped=struct.unpack_from('>IIH2xII',data,blocks[0]+12)
        for field,clock,raw,applied,count,lost,*flags in diagnostics:
            assert count==steps+1, 'Unobserved or repeated movement-clock update'
            assert raw==((clock-previous)&0xffffffff), 'Movement clock lost elapsed time'
            assert applied==max(4,min(50,raw)), 'Incorrect movement clamp'
            assert lost==clipped+max(0,raw-50), 'Unaccounted movement time above cap'
            previous=clock;steps=count;clipped=lost
        assert [d[3] for d in diagnostics[:len(rows)]]==[r[2] for r in rows], 'Movement used a different delta than its clock'
        starts=[int(f) for f in re.findall(r'^PDEVENT (-?\d+) 0xbe12$',log,re.M)]
        ends=[int(f) for f in re.findall(r'^PDEVENT (-?\d+) 0xbef2$',log,re.M)]
        assert len(starts)==len(ends)
        offsets=[]
        for field,clock,*rest in diagnostics:
            paused=sum(max(0,min(field,end)-start) for start,end in zip(starts,ends))
            offsets.append(clock-4*(field-paused))
        assert max(offsets)-min(offsets)<=4, 'Movement clock disagrees with independently counted unpaused VBLs'
        floor_added=sum(max(0,4-d[2]) for d in diagnostics)
        print(f'  {len(diagnostics)} independent movement-clock intervals verified; upper-clamp loss {clipped*5} ms; lower-clamp addition {floor_added*5} ms')

    before=None;contracts=0
    for offset,values in re.findall(r'^PDMREG_EVENT -?\d+ (0x[0-9a-f]+) (.+)$',log,re.M):
        v=list(map(int,values.split()));assert len(v)==19
        if offset=='0xccee':before=v
        else:
            assert before is not None
            product=(signed16(v[17])*signed16(v[18]))&0xffffffff
            assert v[4]==product, 'Displaced signed multiplication changed'
            assert all(v[i]==before[i] for i in range(16) if i!=4), 'Movement clock clobbered a preserved register/stack'
            expected=(before[16]&~15)|(8 if product&0x80000000 else 0)|(4 if product==0 else 0)
            if contracts<len(diagnostics) and len(diagnostics[contracts])==7:
                assert v[16]&~31==before[16]&~31, 'Movement clock changed status bits outside CCR'
                assert diagnostics[contracts][6]&31==expected&31, ('Guest movement CCR differs from native multiplication',before[16],diagnostics[contracts][6],expected)
            else:
                assert v[16]==expected, ('Movement CCR differs from native multiplication',before[16],v[16],expected)
            contracts+=1;before=None
    probes=json.loads((root/'configuration.json').read_text()).get('COVERAGE_PROBES') or ''
    if '0xccf6' in probes:
        assert len(rows)<=contracts<=len(rows)+1, 'Missing wrapper register/CCR samples'
    if contracts:print(f'  {contracts} native register/stack/CCR contracts verified, including X preservation')
