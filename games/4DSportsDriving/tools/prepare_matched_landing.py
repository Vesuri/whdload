#!/usr/bin/env python3
"""Disposable compiled synthetic fixture: identical native car bytes at race start."""
import argparse,hashlib,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1]
source=R/'src'
args=argparse.ArgumentParser();args.add_argument('--name',default='matched-landing');args.add_argument('--capture',default='baseline-landing-contact20');args.add_argument('--sample-tick',type=int);args.add_argument('--memory',default='memory.bin');opts=args.parse_args()
assert '/' not in opts.name and '/' not in opts.capture
base=R/'tmp/fixtures'/opts.name
assert not base.exists()
cap=R/'tmp/prof'/opts.capture
a=json.loads((cap/'anchor.json').read_text());memory=(cap/opts.memory).read_bytes()
o=a['data_base']+0x7ffe-0x92e-a['memory_base']
car=memory[o:o+0xd0]
if opts.sample_tick is not None:
 from simulation_fixture import read_fixture
 sample=next(r for r in read_fixture(cap,opts.memory) if r[0]==opts.sample_tick)
 car=sample[2][0x152:0x222];a['simulation_tick']=sample[0];a['active_simulation_word']=sample[1]
assert len(car)==208
base.mkdir();shutil.copytree(source,base/'source')
p=base/'source/simulation_verify.s';text=p.read_text()
needle=' IFD SIM_A4000\n IFND SIM_A4000_NATIVE\n ; Verification tables can exceed a 68000 relative-call displacement.'
assert text.count(needle)==1
seed=''' ; Disposable matched-state landing fixture. Exact native car structure,
 ; including cached wheel coordinates, from the saved native crest reference.
 ; Both modes get identical bytes; A4000 private fractions start at zero.
 ; Global race/road context remains newly initialized: native reproduction
 ; must be checked before treating this as a natural-state continuation.
 lea .matched_car_data(pc),a0
 lea -$92e(a4),a1
 moveq #51,d0
.matched_car_copy:
 move.l (a0)+,(a1)+
 dbra d0,.matched_car_copy
 bra .matched_car_done
.matched_car_data:
'''
seed+=''.join(' dc.b '+','.join(f'${v:02x}' for v in car[i:i+16])+'\n' for i in range(0,len(car),16))
seed+=' even\n.matched_car_done:\n'
p.write_text(text.replace(needle,seed+needle))
(base/'car.bin').write_bytes(car)
manifest=dict(source_capture=str(cap.relative_to(R)),native_tick=a['simulation_tick'],native_rate=a['active_simulation_word'],car_bytes=len(car),car_sha256=hashlib.sha256(car).hexdigest(),memory_sha256=hashlib.sha256(memory).hexdigest(),scope='Synthetic equal-car-state start. Other race context is initialized normally, and A4000 private fractions are zero. Require live byte checks and native trajectory comparison; not a full replay restore or natural handling gate.')
(base/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
