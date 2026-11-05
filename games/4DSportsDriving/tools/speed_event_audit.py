#!/usr/bin/env python3
"""Audit fixed-decrement reachability and two-car speed event ownership."""
import hashlib,json
from pathlib import Path
import capstone
root=Path(__file__).resolve().parents[1]
code=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()[0x28:0x28+0x3a04c]
checks={0xf742:'30680024',0xf746:'b0e90022',0xf74a:'6f6e',0xf754:'30680024',0xf758:'90e90022',0xf75c:'b0fc07d0',0xf760:'6f2a',0xf78a:'602e',0xf794:'30680022',0xf798:'90e90024',0xf79c:'b0fc07d0',0xf7a0:'6f18',0xf7b6:'0650fb00',0xd970:'4eba3466',0xd97a:'6746',0xd980:'4a2800c8',0xd984:'6638',0xd98e:'4eba24a2',0xfe3a:'117c000100c8',0xfe44:'117c000100c8',0xff46:'4268002c',0xff5a:'9150',0xffec:'3368002c002a',0xfffa:'3368002c002a'}
for at,hexbytes in checks.items():
 b=bytes.fromhex(hexbytes);assert code[at:at+len(b)]==b,hex(at)
# MOVEA.W and SUBA.W sign-extend to 32 bits, so every pair of signed
# words maps to one of these differences, with no 32-bit overflow.
reachable=[d for d in range(-65535,65536) if d>0 and d<=2000 and -d>2000]
assert not reachable
md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000)
def decoded(start,end):
 ins=list(md.disasm(code[start:end],start));assert sum(i.size for i in ins)==end-start
 return [dict(address=hex(i.address),bytes=i.bytes.hex(),instruction=i.mnemonic+' '+i.op_str) for i in ins]
result=dict(original_code_sha256=hashlib.sha256(code).hexdigest(),verified_instruction_sites=len(checks),fixed_decrement=dict(address='0xf7b6',signed_differences_checked=131071,reachable_differences=reachable,conditions=['oldRPM-newRPM > 0','oldRPM-newRPM <= 2000','newRPM-oldRPM > 2000'],scope='Ordinary entry with stable RPM words only. Not an indirect-entry or asynchronous-write proof.',decision='Do not rate-scale this unreachable ordinary-path decrement.'),two_car=dict(caller='0xd98e',callee='0xfe32',gate='Native overlap predicate at 0x10dd8 must succeed; first car +0xc8 must be zero.',latch='Sets both cars +0xc8 to one before modifying velocities.',speed_change='Relative heading/velocity-derived one-call subtraction, saturated at zero; copies target to actual speed for both cars.',decision='Preserve native collision response units. No elapsed-time multiplier.',limits='Latch reset lifecycle and repeated-contact runtime behavior still require collision coverage.'),rpm_instructions=decoded(0xf73a,0xf7ba),collision_instructions=decoded(0xfe32,0x10012),caller_instructions=decoded(0xd970,0xd998))
out=root/'tmp/prof/speed-event-audit.json';out.write_text(json.dumps(result,indent=2)+'\n');print(out);print('24 exact instruction sites; 131071 signed differences; no ordinary-path fixed-decrement reachability')
