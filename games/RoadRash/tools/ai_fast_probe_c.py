import sys,json,re,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);start,end=0x8d2c0,0x8d8d0;entry=read_bytes(s,start,8);assert entry[:2]==bytes.fromhex('4ef9');target=int.from_bytes(entry[2:6],'big');assert 0x200000<=target<0xa00000 or target>=0x1000000
 native=bytearray(read_bytes(s,start,end-start));copied=bytearray(read_bytes(s,target,end-start));fixups=[]
 for addr,hexbytes in [(start,'33fc0000000a594c'),(0x8d40a,'08a900040069'),(0x8d46e,'08a900040069'),(0x8d4e6,'41f9000941d6')]:
  h=read_bytes(s,addr,6);assert h[:2]==bytes.fromhex('4ef9') and int.from_bytes(h[2:6],'big')==target+addr-start
  raw=bytes.fromhex(hexbytes);native[addr-start:addr-start+len(raw)]=raw
 for l in (ROOT/'tmp/ana/game.dis').read_text().splitlines():
  m=re.match(r'^([0-9a-f]{6})\s+([0-9a-f]+)\s+(b(?:sr|ra|eq|ne|pl|mi|cc|cs|hi|ls|gt|ge|lt|le|vs|vc)\.w)\s+\$([0-9a-f]+)',l)
  if not m:continue
  addr,dest=int(m[1],16),int(m[4],16)
  if not start<=addr<end or start<=dest<end:continue
  off=addr-start+2;stub=target+off+struct.unpack_from('>h',copied,off)[0]
  assert read_bytes(s,stub,6)==bytes.fromhex('4ef9')+dest.to_bytes(4,'big')
  copied[off:off+2]=native[off:off+2];fixups.append(dict(source=hex(addr),target=hex(dest),stub=hex(stub)))
 assert len(fixups)==25 and copied==native
 assert read_bytes(s,target+end-start,6)==bytes.fromhex('4ef9')+end.to_bytes(4,'big')
 result=dict(target=hex(target),bytes_equal=len(copied),fixups=fixups,provenance=provenance(os.environ['SLAVE'],s));(s.out/'probe.json').write_text(json.dumps(result,indent=2)+'\n');print(target,len(fixups),flush=True)
finally:s.quit()
