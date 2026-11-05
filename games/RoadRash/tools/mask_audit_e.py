import sys,json,struct,re
from harness_a import *
lst=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',lst,re.M)[1],16)
s=Session(sys.argv[1]);rows=[]
try:
 route(s);base=rd(s,0xafd62)-sym('e_background_road');s.input('JOY2_UP',1)
 for tick in [100,300,600,1000]:
  if tick>100:advance(s,tick)
  s.cmd('tbreak *0xb076e');s.cmd('continue',timeout=60)
  table=rd(s,base+sym('e_mask_table'));cursor=rd(s,base+sym('e_mask_cursor'));data=read_bytes(s,table,32768);chip=read_bytes(s,0,0x100000);count=0;errors=[]
  for i in range(0,len(data),16):
   key,mask,w,h=struct.unpack_from('>IIHH',data,i)
   if not key:continue
   count+=1;assert 0x80010<=mask and mask+w*h<=cursor<=0xbc3ec
   for y in range(h):
    for x in range(0,w,2):
     want=0
     for plane in range(4):want|=struct.unpack_from('>H',chip,key+y*w*4+plane*w+x)[0]
     got=struct.unpack_from('>H',chip,mask+y*w+x)[0]
     if got!=want:errors.append([hex(key),y,x,hex(got),hex(want)])
  rows.append(dict(field=field(s),entries=count,bytes=cursor-0x80010,errors=errors[:20],error_count=len(errors)));print(rows[-1],flush=True)
  assert not errors
 (s.out/'audit.json').write_text(json.dumps(rows,indent=2))
finally:s.quit()
