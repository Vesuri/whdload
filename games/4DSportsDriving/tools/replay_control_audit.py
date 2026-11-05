#!/usr/bin/env python3
"""Audit original replay toolbar targets and explicit speed-byte references.
Every aligned offset is scanned to avoid linear disassembly stopping at tables.
This is not an exhaustive proof about indirect/aliased memory writes.
"""
import hashlib,json,struct
from pathlib import Path
import capstone
root=Path(__file__).resolve().parents[1]
p=root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts'
raw=p.read_bytes();code=raw[0x28:0x28+0x3a04c]
md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000)
refs=[]
for off in range(0,len(code)-2,2):
    for i in md.disasm(code[off:off+16],off,count=1):
        if '$3d(a4)' in i.op_str:
            refs.append(dict(offset=hex(off),bytes=i.bytes.hex(),instruction=i.mnemonic+' '+i.op_str))
assert [int(x['offset'],16) for x in refs]==[0x6f98,0x7a1c,0x9db0,0xa478,0xa52e]
assert code[0xa478:0xa47c]==bytes.fromhex('422c003d')
assert code[0xa52e:0xa534]==bytes.fromhex('197c0003003d')
targets=[0xa558+x for x in struct.unpack_from('>7h',code,0xa53c)]
assert targets==[0xa08a,0xa268,0xa520,0xa478,0xa494,0xa4c4,0x9c26]
names=['forward seek','backward seek','double play','normal play','pause','rewind to zero','menu']
# Scheduler branches selector 2 to half and selector 3 to double.
assert code[0x7a4c:0x7a56]==bytes.fromhex('554067d4534067e460ee')
report=dict(original_stunts_sha256=hashlib.sha256(raw).hexdigest(),direct_speed_references=refs,toolbar=[dict(selection=i,target=hex(t),action=n) for i,(t,n) in enumerate(zip(targets,names))],native_scheduler={'2':'half','3':'double','other':'normal'},conclusion='The seven original toolbar actions contain no half-speed selector. The aligned direct-reference scan finds three clears and one write of 3; no write of 2. Half-speed exists in the timer decoder but native UI reachability is not established. This audit does not exclude indirect aliases, wider overlapping writes, or other executable hunks. Preserve the branch and test it explicitly without claiming native UI coverage.')
out=root/'tmp/replay-speeds-runtime-67/control-audit.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
