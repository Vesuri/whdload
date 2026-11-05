import sys,json,struct
from harness_a import *
s=Session(sys.argv[1]);rows=[];held={};last_drive=0
try:
 route(s);s.input('JOY2_UP',1);s.cmd('break *0x87670')
 for i in range(5000):
  s.cmd('continue',timeout=60)
  b=read_bytes(s,0xa5d00,0x11e0)
  ptrs=struct.unpack('>36I',read_bytes(s,0x909cc,144));active=[]
  for p in ptrs:
   if p==0xffffffff:break
   active.append(p)
  n=rd(s,0xa8734,2)
  rows.append(dict(field=struct.unpack_from('>I',b,0x4c)[0],state=b.hex(),active=active,objects=read_bytes(s,0xa7c3e,n*20).hex()))
  if i%250==0:
   print(i,rows[-1]['field'],flush=True)
   (s.out/'trace.json').write_text(json.dumps(rows))
  if os.environ.get('VIS_DRIVE') and rows[-1]['field']>=last_drive+20:
   last_drive=rows[-1]['field'];lat=struct.unpack_from('>h',b,0x90)[0];riding=struct.unpack_from('>b',b,0xce)[0]<0
   wanted={'JOY2_UP':int(riding),'JOY2_LEFT':int(riding and lat>64),'JOY2_RIGHT':int(riding and lat<-64)}
   for k,v in wanted.items():
    if held.get(k)!=v:s.input(k,v);held[k]=v
  if rows[-1]['field']>int(os.environ.get('VIS_END','6000')):break
 (s.out/'trace.json').write_text(json.dumps(rows))
 (s.out/'provenance.json').write_text(json.dumps(provenance(os.environ['SLAVE'],s),indent=2))
finally:s.quit()
