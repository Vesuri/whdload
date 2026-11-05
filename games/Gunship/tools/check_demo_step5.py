"""Compare unattended native/enhanced attract mode; no injected play input."""
import sys,os,json,struct
from session_b import Session
from layout import locate
s=Session(sys.argv[1],dict(AMIGA_SETUP='a1200-fast',EXTRA_ARGS='--video_driver=null',WHD_ARGS='CUSTOM1='+os.environ.get('ENHANCED','1')))
try:
 for n in [2000,2000,2000,500]:s.fields(n)
 s.shot('start.png')
 mem=s.read(0x200000,0x800000);h=locate(mem)['hunks'];rows=[]
 for i in range(11):
  p=s.read(h[6]+0x3b88,86)
  rows.append(dict(field=s.field,tick=int.from_bytes(p[12:14],'big'),x=int.from_bytes(p[:2],'big'),y=int.from_bytes(p[2:4],'big'),height=int.from_bytes(p[28:30],'big'),rpm=p[27],engine=p[66],heading=p[53],pitch=p[54],roll=p[55],demo=s.read(h[6]+0x1c5,2).hex(),tape=s.read(h[6]+0x45ce,8).hex(),player=p.hex()))
  if i<10:s.fields(100)
 s.shot('end.png');s.key('space',1);s.fields(10);s.key('space',0);s.fields(100);s.shot('exit.png')
 (s.out/'demo.json').write_text(json.dumps(dict(hunks=h,enhanced=os.environ.get('ENHANCED','1'),rows=rows),indent=2))
 print(json.dumps(rows),flush=True)
finally:s.quit()
