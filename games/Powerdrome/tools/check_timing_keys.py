#!/usr/bin/env python3
"""Audit centering commands and movement-time modifiers against producer timestamps.

The bounded C-key fixture publishes nine commands; --pause checks the pause fixture
with no centering commands; --forces checks mixed C/X/Z and steering. These routes
do not wrap either queue.
This is not hardware-keyboard or arbitrary-mode coverage.
"""
import argparse
import json
from pathlib import Path
import re
import struct
from coverage_status import fixture


def locate(data, tag):
    world=[m.start() for m in re.finditer(b'PDW20T01',data)
           if struct.unpack_from('>H',data,m.start()+8)[0]==1]
    assert len(world)==1
    found=[m.start() for m in re.finditer(tag,data) if 0<m.start()-world[0]<4096]
    assert len(found)==1
    return found[0]


p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
routes=p.add_mutually_exclusive_group()
routes.add_argument('--pause',action='store_true',help='Audit movement modifiers and ignored non-centering keys in CUSTOM5=8')
routes.add_argument('--forces',action='store_true',help='Audit C/X/Z and steering input in CUSTOM5=11')
a=p.parse_args();histories=[]
for root in a.captures:
    cfg=json.loads((root/'configuration.json').read_text())
    commands=[] if a.pause else [(10+20*i,'c') for i in range(9)]
    route,fields=(8,300) if a.pause else (3,500)
    if a.forces:
        route,fields=11,750
        commands=[(10,'c'),(30,'c'),(50,'c'),(90,'x'),(110,'x'),(130,'x'),(150,'x'),(170,'c'),(190,'c'),(230,'z'),(320,'c'),(340,'c'),(550,'z')]
    count=len(commands)
    assert re.search(rf'\bCUSTOM5={route}\b',cfg['WHD_ARGS']) and int(cfg['FIELDS'])==fields
    epoch=fixture(root/'code.bin')['epoch']*4
    initial=(root/'code.bin').read_bytes();final=(root/'final-code.bin').read_bytes()
    ki=locate(initial,b'PDKEY001');kf=locate(final,b'PDKEY001')
    before=struct.unpack_from('>6H4I',initial,ki+8)
    after=struct.unpack_from('>6H4I',final,kf+8)
    assert before[0]==after[0]==1
    assert before[4:9]==(0,0,0,0,0)
    assert after[4:9]==(8*count,8*count,count,count,0), 'Missing, repeated or overflowing centering commands'
    game=int((root/'game-base.txt').read_text(),0)
    assert after[1]==0, 'Unpresented centering feedback'
    if count:
        expected_digit='2' if a.forces else '9'
        assert (root/'final-chip.bin').read_bytes()[game+0x3c17]==ord(expected_digit), 'Final centering feedback was not presented'
    keys=[struct.unpack_from('>IH2x',final,kf+36+8*i) for i in range(count)]
    expected=[(epoch+(field+1)*4,ord(key)) for field,key in commands]
    assert keys==expected, ('Commands disagree with the independently timed key fixture',keys,expected)
    inputs=[m.start() for m in re.finditer(b'PDINPT02',final)
            if struct.unpack_from('>I',final,m.start()+12)[0]]
    assert len(inputs)==1
    ip=inputs[0]
    produced,consumed,overflow=struct.unpack_from('>III',final,ip+24)
    assert overflow==0 and 0<produced<255 and consumed<=produced
    events=[struct.unpack_from('>I2xH',final,ip+64+16*i)
            for i in range(produced)]
    rows=[]
    for v in re.findall(r'^PDKEY_EVENT -?\d+ 0xccee (.+)$',(root/'swaps-gdb.txt').read_text(),re.M):
        v=list(map(int,v.split()));assert len(v)==15
        clock,enabled,pending,cursor,modifier,read,write,generated,applied,lost,last,on,strength,mode,disabled=v
        due=[key for key in keys if key[0]<=clock]
        expected_mod=before[3]
        input_count=0
        for timestamp,value in events:
            if timestamp>clock:break
            expected_mod=value;input_count+=1
        assert modifier==expected_mod and cursor==16*input_count, ('Movement did not use its historical modifier',clock,modifier,expected_mod,cursor,input_count)
        assert applied==len(due) and read==8*len(due), ('Command applied at the wrong world time',clock,applied,due)
        assert last==(due[-1][0] if due else 0)
        expected_strength=0
        for _,key in due:
            if key==ord('c'):expected_strength=min(360,expected_strength+40)
            elif key==ord('x'):expected_strength=max(0,expected_strength-40)
            elif key==ord('z'):expected_strength=0
            else:raise AssertionError('Unsupported fixture key')
        assert strength==expected_strength and on==(65535 if expected_strength else 0), ('Centering changed outside the expected command history',clock,on,strength,due)
        assert enabled and not lost and applied<=generated<=len(keys)
        rows.append((clock-epoch,modifier,on,strength,applied,last-epoch if last else 0))
    assert len(rows)>=(650 if a.forces else 200 if a.pause else 450)
    histories.append(rows)
    print(f'{root.name}: {len(keys)} exact producer timestamps; {len(rows)} movement-time modifier/centering states verified; no queue loss')
if len(histories)>1:
    length=min(map(len,histories))
    for rows in histories[1:]:assert rows[:length]==histories[0][:length], 'Centering/input histories differ across CPUs'
    print(f'{length} common centering/modifier states match at identical world times')
