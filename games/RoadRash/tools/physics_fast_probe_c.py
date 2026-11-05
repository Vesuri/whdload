import sys,json,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);m=json.loads((ROOT/'tmp/c-physics-fast-source/manifest.json').read_text());lo=m['start'];hi=m['end'];base=rd(s,lo+2);assert 0x200000<=base<0xa00000 or base>=0x1000000
 native=bytearray(read_bytes(s,lo,hi-lo));copied=bytearray(read_bytes(s,base,hi-lo));original=(ROOT/'tmp/c-actor-memory-audit/main-field100.bin').read_bytes()
 for a in m['entries']:
  assert read_bytes(s,a,2)==bytes.fromhex('4ef9') and rd(s,a+2)==base+a-lo
  native[a-lo:a-lo+6]=original[a-0x80000:a-0x80000+6]
 for off,t in m['fixups']:
  stub=base+off+struct.unpack_from('>h',copied,off)[0]
  assert read_bytes(s,stub,6)==bytes.fromhex('4ef9')+t.to_bytes(4,'big')
  copied[off:off+2]=native[off:off+2]
 assert native==copied,next((hex(lo+i) for i,(a,b) in enumerate(zip(native,copied)) if a!=b),None)
 r=dict(bytes_equal=len(native),base=hex(base),fixups=len(m['fixups']),entries=len(m['entries']),provenance=provenance(os.environ['SLAVE'],s));(s.out/'probe.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
finally:s.quit()
