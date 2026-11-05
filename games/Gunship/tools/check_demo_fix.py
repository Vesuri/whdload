"""Normal-startup demo playback and real-key exit; production slaves only."""
from session_b import Session
from pathlib import Path
import os,sys,json
ntsc=os.environ.get('NTSC','0')=='1';custom=os.environ.get('ENHANCED','1')
s=Session(sys.argv[1],dict(AMIGA_SETUP='a1200-fast',NTSC=str(int(ntsc)),EXTRA_ARGS='--video_driver=null',WHD_ARGS='CUSTOM1='+custom))
try:
 for n in [2000,2000,2000,500]:s.fields(n)
 mem=s.read(0x200000,0x800000)
 sig=bytes.fromhex('4cdf4cfc' if ntsc else '51cfffce');hits=[];pos=0
 while True:
  pos=mem.find(sig,pos)
  if pos<0:break
  off=pos-0x2f2a
  if off>=8 and int.from_bytes(mem[off-8:off-4],'big')==(61748 if ntsc else 61640)+8:hits.append(off+0x200000)
  pos+=1
 assert len(hits)==1,hits
 h=[];ptr=hits[0]
 for _ in range(9):h.append(ptr);ptr=int.from_bytes(s.read(ptr-4,4),'big')*4+4
 def sample():
  p=s.read(h[6]+0x3b88,86)
  return dict(field=s.field,tick=int.from_bytes(p[12:14],'big'),xy=p[:4].hex(),height=int.from_bytes(p[28:30],'big'),rpm=p[27],demo=s.read(h[6]+0x45cc,1).hex(),tape=int.from_bytes(s.read(h[6]+0x45d2,4),'big'))
 s.shot('start.png');rows=[sample()]
 for _ in range(10):s.fields(100);rows.append(sample())
 s.shot('end.png');s.tap('space');s.fields(100);s.shot('exit.png');ex=sample()
 result=dict(ntsc=ntsc,custom1=custom,hunks=h,rows=rows,exit=ex,ticks=(rows[-1]['tick']-rows[0]['tick'])&65535,tape_bytes=rows[-1]['tape']-rows[0]['tape'])
 (s.out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 assert rows[0]['demo']=='01' and rows[-1]['demo']=='01'
 assert rows[-1]['xy']!=rows[0]['xy'] and result['tape_bytes']>0
finally:s.quit()
