import sys,json,struct,os
from harness_a import *
s=Session(sys.argv[1]);rows=[];held={};last_drive=0
try:
 route(s);s.input('JOY2_UP',1);advance(s,int(os.environ.get("HEIGHT_START","400")));s.cmd('break *0x87670')
 track=read_bytes(s,0xa851a,512);(s.out/'track.bin').write_bytes(track)
 while True:
  s.cmd('continue',timeout=60);b=read_bytes(s,0xa5d00,0xe0);n=rd(s,0xa8734,2)
  rows.append(dict(track=read_bytes(s,0xa851a,512).hex(),field=struct.unpack_from('>I',b,0x4c)[0],state=b.hex(),geometry=read_bytes(s,0xa6f3c,128).hex(),road_y=read_bytes(s,0xa7068,64).hex(),objects=read_bytes(s,0xa7c3e,n*20).hex()))
  if os.environ.get('HEIGHT_DRIVE') and rows[-1]['field']>=last_drive+20:
   last_drive=rows[-1]['field'];lat=struct.unpack_from('>h',b,0x90)[0];riding=struct.unpack_from('>b',b,0xce)[0]<0
   for k,v in {'JOY2_UP':int(riding),'JOY2_LEFT':int(riding and lat>64),'JOY2_RIGHT':int(riding and lat<-64)}.items():
    if held.get(k)!=v:s.input(k,v);held[k]=v
  if len(rows)%250==0:
   print(len(rows),rows[-1]['field'],flush=True);(s.out/'trace.json').write_text(json.dumps(rows))
  if rows[-1]['field']>=int(os.environ.get('HEIGHT_END','600')):break
 (s.out/'trace.json').write_text(json.dumps(rows,indent=2));(s.out/'provenance.json').write_text(json.dumps(provenance(os.environ['SLAVE'],s),indent=2))
 print(len(rows),'frames',flush=True)
finally:s.quit()
