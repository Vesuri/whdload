#!/usr/bin/env python3
"""Controlled airborne entry diagnostic; no production physics changes."""
from pathlib import Path
import shutil,struct,json,hashlib
from simulation_fixture import read_fixture
source=Path('src')
base=next(s for t,h,s in read_fixture('tmp/prof/crest-d9e7903','bridge-end.bin') if t==580)
native=next(s for t,h,s in read_fixture('tmp/prof/natural-crest20','bridge-end.bin') if t==232)
car=base[0x152:0x222];private=base[0x466:0x466+152];rng=base[0x460:0x466]
assert len(car)==208 and len(private)==152 and len(rng)==6
for name,changed in [('flight580-control',False),('flight580-native-velocity',True)]:
 dst=Path('tmp/fixtures')/name;assert not dst.exists();shutil.copytree(source,dst/'source')
 c=bytearray(car);v=bytearray(private)
 if changed:
  c[0x4c:0x54]=native[0x152+0x4c:0x152+0x54]
  for w in range(4):struct.pack_into('>h',v,8+4*w,0)
 data=bytes(c+v+rng);original=car+private+rng
 differences=[i for i,(a,b) in enumerate(zip(original,data)) if a!=b]
 assert not changed or all(0x4c<=i<0x54 or i in [208+8+4*w+j for w in range(4) for j in (0,1)] for i in differences)
 seed=''' ; Isolated airborne continuation: exact car, private fractions and RNG.
 ; Other race context is initialized normally; require natural reproduction.
 lea .flight_seed_data(pc),a0
 lea -$92e(a4),a1
 moveq #51,d0
.flight_car:
 move.l (a0)+,(a1)+
 dbra d0,.flight_car
 lea sim_fixture_before(pc),a1
 adda.l #sim_a4000_private-sim_fixture_before,a1
 moveq #37,d0
.flight_private:
 move.l (a0)+,(a1)+
 dbra d0,.flight_private
 lea $228(a4),a1
 moveq #2,d0
.flight_rng:
 move.w (a0)+,(a1)+
 dbra d0,.flight_rng
 bra .flight_seed_done
.flight_seed_data:
'''
 seed+=''.join(' dc.b '+','.join(f'${x:02x}' for x in data[i:i+16])+'\n' for i in range(0,len(data),16))
 seed+=' even\n.flight_seed_done:\n'
 p=dst/'source/simulation_verify.s';s=p.read_text();needle='.active:\n ; Throttle throughout';assert s.count(needle)==1;p.write_text(s.replace(needle,seed+needle))
 (dst/'seed.bin').write_bytes(data)
 report=dict(base_capture='crest-d9e7903',base_tick=580,native_tick=232,velocity_override=changed,seed_sha256=hashlib.sha256(data).hexdigest(),differences=differences,velocities=[struct.unpack_from('>h',c,0x4c+2*w)[0]+struct.unpack_from('>h',v,8+4*w)[0]/5 for w in range(4)],scope='Compiled one-time seed after private initialization. Velocity-only counterfactual; global race context is fresh. Must reproduce original continuation with control seed before interpreting the intervention. Not a proposed runtime law or acceptance result.')
 (dst/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(name,report['velocities'],differences)
