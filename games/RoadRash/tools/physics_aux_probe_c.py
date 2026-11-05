import sys,json,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);m=json.loads((ROOT/'tmp/c-physics-aux-source/manifest.json').read_text());original=(ROOT/'tmp/c-actor-memory-audit/main-field100.bin').read_bytes();bases={a:rd(s,a+2) for a,z in m['ranges']};checked=0
 for a,z in m['ranges']:
  base=bases[a];assert 0x200000<=base<0xa00000 or base>=0x1000000
  native=bytearray(read_bytes(s,a,z-a));copied=bytearray(read_bytes(s,base,z-a))
  for t in m['entries']:
   if a<=t<z:
    assert read_bytes(s,t,2)==bytes.fromhex('4ef9') and rd(s,t+2)==base+t-a
    native[t-a:t-a+6]=original[t-0x80000:t-0x80000+6]
  for owner,off,t in m['fixups']:
   if owner!=a:continue
   dest=base+off+struct.unpack_from('>h',copied,off)[0];mapped=next((bases[x]+t-x for x,y in m['ranges'] if x<=t<y),None)
   if mapped is not None:assert dest==mapped
   else:assert read_bytes(s,dest,6)==bytes.fromhex('4ef9')+t.to_bytes(4,'big')
   copied[off:off+2]=native[off:off+2]
  assert native==copied,hex(a);checked+=len(copied)
  assert read_bytes(s,base+z-a,6)==bytes.fromhex('4ef9')+z.to_bytes(4,'big')
 main=rd(s,0x8b488);fm=json.loads((ROOT/'tmp/c-physics-fast-source/manifest.json').read_text());direct=0
 for off,t in fm['fixups']:
  stub=main+off+struct.unpack('>h',read_bytes(s,main+off,2))[0]
  if t in (0x8da5c,0x8e166):
   raw=read_bytes(s,stub,6);assert raw[:2]==bytes.fromhex('4efa') and raw[4:]==bytes.fromhex('4e71')
   dest=stub+2+struct.unpack_from('>h',raw,2)[0];assert dest==bases[t];direct+=1
  else:assert read_bytes(s,stub,6)==bytes.fromhex('4ef9')+t.to_bytes(4,'big')
 assert direct==3
 r=dict(direct_helper_branches=direct,bytes_equal=checked,bases={hex(a):hex(v) for a,v in bases.items()},fixups=len(m['fixups']),entries=len(m['entries']),provenance=provenance(os.environ['SLAVE'],s));(s.out/'probe.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
finally:s.quit()
