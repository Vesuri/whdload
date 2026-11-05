from pathlib import Path
import re,json,struct,sys
r=Path(__file__).resolve().parents[1];stage=int(sys.argv[1]);rows=json.loads((r/'manifest/step5-b6-division-sites.json').read_text());mul=json.loads((r/'manifest/step5-b6-multiply-sites.json').read_text()) if stage>=2 else []
for p in ('a1200-fast','a1200'):
 for variant in ('verify','lean'):
  d=r/f'tmp/step5/{p}-b6-s{stage}-matrix-{variant}-fine';mem=(d/'loop126.bin').read_bytes();listing=(r/f'tmp/build/step5-b6-s{stage}/{variant}/fine.list').read_text();syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)};base=struct.unpack_from('>I',mem,0x654e8)[0]-syms['barrier']
  for x in rows:
   pc=x['pc'];expected=bytes.fromhex('4c4108014e71') if x['constant'] is not None else bytes.fromhex('4eb9')+struct.pack('>I',base+syms['FF1NativeDivide'])
   assert mem[pc:pc+6]==expected,(p,variant,hex(pc))
  for x in mul:assert mem[x['pc']:x['pc']+6]==bytes.fromhex('4c0108004e71')
  if stage>=3:assert mem[0x6977a:0x69782]==bytes.fromhex('4ef9')+struct.pack('>I',base+syms['FF1NativeLookahead'])+bytes.fromhex('4e71')
  if stage>=4:
   code=(r/f'tmp/build/step5-b6-s{stage}/{variant}/fine.bin').read_bytes();q=syms['FF1TrigReplacement'];assert mem[0x24fe0:0x25020]==code[q:q+64]
  if stage>=5:
   assert mem[0x29500:0x29506]==bytes.fromhex('4ef9')+struct.pack('>I',base+syms['FF1NativeMultiply'])
   for x in json.loads((r/'manifest/step5-b6-cfg-sites.json').read_text()):
    expected=bytes.fromhex('4c0108004e71') if x['kind']=='multiply' else bytes.fromhex('4eb9')+struct.pack('>I',base+syms['FF1NativeDivide'])
    assert mem[x['pc']:x['pc']+6]==expected,(p,variant,hex(x['pc']))
  print(p,variant,'verified',len(rows),'division and',len(mul),'multiply patches')
