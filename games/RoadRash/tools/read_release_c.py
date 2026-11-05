import sys,json,os,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);target=rd(s,0x8f57c);data=read_bytes(s,target,160);off=data.find(b'RRSTART2');assert off>=0
 record=read_bytes(s,target+off+8,400);count,live,cursor,delta,starter=struct.unpack_from('>IIIHH',record);assert count==1
 (s.out/'capture.bin').write_bytes(record)
 result=dict(live=live,cursor=cursor,delta=delta,starter=starter,actors={hex(a):record[16+i*128:16+(i+1)*128].hex() for i,a in enumerate([0xa5d60,0xa61e0,0xa6260])},provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('release',live,cursor,delta,starter,flush=True)
finally:s.quit()
