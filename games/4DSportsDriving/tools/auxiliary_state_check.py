#!/usr/bin/env python3
"""Check expanded state lifecycle and unchanged pre-hook race trajectories."""
import argparse,json,struct
from pathlib import Path
from simulation_fixture import read_fixture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('reference',type=Path);a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();r=(a.reference/'memory.bin').read_bytes();m=json.loads((a.capture/'anchor.json').read_text());rm=json.loads((a.reference/'anchor.json').read_text())
assert m['simulation_tick']==rm['simulation_tick']
checks={b'4DHISTST':(5,40,40),b'4DAUXTST':(1,1186,1186),b'4DSCHTST':(1,2,2)}
for marker,want in checks.items():
 i=b.index(marker);assert struct.unpack_from('>HHI',b,i+8)==want,marker
aux=b.index(b'4DAUXPHY')+12;assert struct.unpack_from('>HH',b,aux-4)==(1,192)
assert b[aux+192:aux+196]==b'AUXG' and not any(b[aux:aux+192])
left=read_fixture(a.capture);right=read_fixture(a.reference);assert len(left)==len(right)==32
for (t,hz,now),(rt,rhz,old) in zip(left,right):
 assert (t,hz)==(rt,rhz) and len(now)==1478 and len(old)==1286
 assert now[:1286]==old and not any(now[1286:]),t

def race(blob,meta):
 x=meta['data_base']+0x7ffe-meta['memory_base'];ph=blob.index(b'4DA4PHYS')+12;tm=blob.index(b'4DTSTATE')+12
 return blob[x-0xa80:x-0x620]+blob[x+0x228:x+0x22e]+blob[ph:ph+128]+blob[tm:tm+32]
assert race(b,m)==race(r,rm)
result=dict(history_checks=40,reset_checks=2,arithmetic_checks=1186,equal_legacy_sample_bytes=1286,equal_samples=32,auxiliary_bytes=192,auxiliary_zero=True,auxiliary_guard=True,physics_hooks_installed='sim_aux_move_stub' in (a.capture/'slave.lst').read_text(encoding='latin1'))
(a.capture/'auxiliary-state-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
