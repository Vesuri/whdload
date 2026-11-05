#!/usr/bin/env python3
"""VERIFY CUSTOM3 boundaries, installed bytes, option isolation and model checks."""
from pathlib import Path
import hashlib,json,struct,sys
from td_report import game_bytes
root=Path(__file__).resolve().parents[1];b=game_bytes()[0x28:0x28+0x7c0c]
patches={0x230:(bytes.fromhex('4eac81464840'),None),0x5314:(bytes.fromhex('397900dff0069bd8'),bytes.fromhex('397c12349bd84e71')),0x5334:(bytes.fromhex('303900dff006'),bytes.fromhex('42404e714e71'))}
for off,(old,new) in patches.items():assert b[off:off+len(old)]==old
incoming=[]
for a in range(0,len(b)-6,2):
 w=int.from_bytes(b[a:a+2],'big');target=None
 if w>>12==6:
  d=struct.unpack('b',b[a+1:a+2])[0]
  if not d:d=struct.unpack('>h',b[a+2:a+4])[0]
  target=a+2+d
 elif w&0xf0f8==0x50c8 or w in (0x4eba,0x4efa):target=a+2+struct.unpack('>h',b[a+2:a+4])[0]
 elif w in (0x4eb9,0x4ef9):target=int.from_bytes(b[a+2:a+6],'big')
 for off,(old,new) in patches.items():
  if target is not None and off<=target<off+len(old):
   incoming.append([hex(a),hex(target)]);assert target==off,'direct branch into rewritten instruction'
normal=root/'tmp/build/release/TestDrive.Slave'
assert hashlib.sha256(normal.read_bytes()).hexdigest()=='ca765222b4257e060e684b80581ed45506d8167c98c016c6d088ad066d6750d4'
for name,on in [(sys.argv[1],True)]+([(sys.argv[2],False)] if len(sys.argv)>2 else []):
 p=Path(name);meta=json.loads((p/'capture.json').read_text());ram=(p/'code.bin').read_bytes();hb=meta['regions']['td']-meta['base']
 for off,(old,new) in patches.items():
  if off==0x230 and on:
   assert ram[hb+off:hb+off+2]==bytes.fromhex('4eb9')
   target=int.from_bytes(ram[hb+off+2:hb+off+6],'big')-meta['base']
   assert ram[target:target+14]==bytes.fromhex('397c12349bd84eac814648404e75')
  else:assert ram[hb+off:hb+off+len(old)]==(new if on else old),(name,hex(off))
 if on:
  start=json.loads((p/'start-state.json').read_text())
  assert (start['rng'],start['race_car'])==(0x1dc9,0)
 # Everywhere else in the RNG, the original implementation is retained exactly.
 for off in range(0x530e,0x5344):
  if not any(p<=off<p+len(old) for p,(old,new) in patches.items()):assert ram[hb+off]==b[off]
print(json.dumps(dict(normal_unchanged=True,patch_boundaries='6-byte demo call+swap; 8-byte seed load; 6-byte beam operand load',incoming_candidates=incoming,first_demo_seed='0x1dc9',first_demo_car_index=0,checks='installed on/off bytes as supplied; unchanged remaining RNG bytes; observed race seed and car',indirect_target_limit='static branch scan does not prove indirect targets'),indent=2))
