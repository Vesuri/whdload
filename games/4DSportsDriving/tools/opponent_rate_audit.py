#!/usr/bin/env python3
"""Native AI decision and RNG-callsite inventory for the supplied executable.
This is a static inventory, not proof of every indirect call or UI lifecycle.
"""
from pathlib import Path
import capstone,struct,json,hashlib
root=Path(__file__).resolve().parents[1]
raw=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
code=raw[40:40+0x3a04c];data=raw[0x3a1dc:0x3a1dc+0x503c]
m=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000)
vector=-0x7ef0
assert data[0x7ffe+vector:0x7ffe+vector+6]==bytes.fromhex('4ef900011e1c')
expected=[0x5c96,0x5caa,0x5cee,0x6f14,0x11a50,0x11a66,0x11aa6,0x1a044,0x1a562,0x22c7a,0x22c9e,0x22cc4]
found=[]
for p in range(0,len(code)-6,2):
 op=struct.unpack_from('>H',code,p)[0];target=None
 if op in (0x4eba,0x4efa,0x6100):target=p+2+struct.unpack_from('>h',code,p+2)[0]
 if op in (0x4eb9,0x4ef9):target=struct.unpack_from('>I',code,p+2)[0]
 if 0x6101<=op<=0x61fe:target=p+2+struct.unpack('b',bytes([op&255]))[0]
 if target==0x11e1c or (op in (0x4eac,0x4eec) and struct.unpack_from('>h',code,p+2)[0]==vector):found.append(p)
assert found==expected
ai=list(m.disasm(code[0xbc48:0xc270],0xbc48))
path=list(m.disasm(code[0x109c2:0x10dd8],0x109c2))
assert sum(i.size for i in ai)==0xc270-0xbc48
assert sum(i.size for i in path)==0x10dd8-0x109c2
assert not [i for i in path if i.mnemonic in ('jsr','bsr','jmp')]
assert not any(0xbc48<=p<0xc270 or 0x109c2<=p<0x10dd8 for p in found)
# The counter advances a spatial subtarget, not a clock: these are the only
# increments, and both feed the path constructor as its subtarget argument.
assert [(i.address,i.op_str) for i in ai if i.mnemonic=='addq.b' and '$790' in i.op_str]==[(0xbd76,'#$1, -$790(a4)'),(0xbfc0,'#$1, -$790(a4)')]
assert [(i.address,i.op_str) for i in path if i.op_str.startswith('$e(a5)')]==[(0x10a3e,'$e(a5), d0'),(0x10a52,'$e(a5), d1'),(0x10dbc,'$e(a5), d0')]
assert code[0xbd66:0xbd6e]==bytes.fromhex('0c6d00c8fffe6c50')
assert code[0xbfb2:0xbfba]==bytes.fromhex('0c4001006f50486c')
result={'rng_vector':hex(vector),'rng_calls':[hex(p) for p in found],
 'opponent_instructions':len(ai),'waypoint_builder_instructions':len(path),
 'waypoint_builder_calls':0,'ai_rng_calls':0,
 'spatial_subtarget_increments':['0xbd76','0xbfc0'],
 'waypoint_builder_sha256':hashlib.sha256(code[0x109c2:0x10dd8]).hexdigest(),
 'decision':'Retain full50Hz spatial target/avoidance/throttle evaluation. Existing steering and braking hooks convert actual rates. No20Hz decision phase or RNG throttle.',
 'scope':'Direct/vector call inventory and native AI/path routines; modal/cosmetic RNG lifecycle remains a separate acceptance task.'}
print(json.dumps(result,indent=2))
