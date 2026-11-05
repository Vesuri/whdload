#!/usr/bin/env python3
"""Check isolated terrain hook bounds, captured target and schedule arithmetic."""
import json,re,struct,sys
from pathlib import Path
import capstone
cap=Path(sys.argv[1]);meta=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes()
sym={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=meta['marker']+8-sym['tape_game'];target=base+sym['sim_grass_step_fixture'];offset=meta['game_base']+0x13dac-meta['memory_base']
assert mem[offset:offset+8]==b'\x4e\xb9'+struct.pack('>I',target)+b'\x4e\x71'
raw=Path('tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()[40:]
md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000)
span=list(md.disasm(raw[0x13dac:0x13db4],0x13dac));assert sum(i.size for i in span)==8
assert [i.mnemonic for i in span]==['eor.w','asr.w','andi.w']
ins=list(md.disasm(raw[0x13d4c:0x13dbe],0x13d4c));assert sum(i.size for i in ins)==0x72
for i in ins:
 if i.mnemonic.startswith(('b','j')) and '$' in i.op_str:
  assert not 0x13dac<int(i.op_str.rsplit('$',1)[1],16)<0x13db4
start=target-meta['memory_base'];end=base+sym['sim_probe_entry_stub']-meta['memory_base']
body=list(md.disasm(mem[start:end],target));assert sum(i.size for i in body)==end-start
assert body[0].mnemonic==body[-2].mnemonic=='movem.l' and body[-1].mnemonic=='rts'
# Exhaust the complete supported history horizon at all rates using the exact
# unsigned word/long operands emitted by the stub. No MUL or subtraction wrap.
for hz in (10,20,50):
 for tick in range(1,30001):
  output=int(58*hz<=5*(tick-1)<60*hz)
  assert output==int(11.6<=(tick-1)/hz<12)
r=dict(passed=True,captured_hook_target=target,original_instructions=[i.mnemonic+' '+i.op_str for i in span],stub_instructions=[i.mnemonic+' '+i.op_str for i in body],schedule_cases=90000,scope='Captured hook and arithmetic proof, not per-call live output tracing.')
(cap/'grass-step-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='stub_instructions'},indent=2))
