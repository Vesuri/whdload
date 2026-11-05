import sys,json,hashlib
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s);tape=json.loads(Path('tmp/c-approved-motion-driven-finish/driven-tape.json').read_text());schedule={}
 for t,k,v in tape['events']:schedule.setdefault(t,[]).append((k,v))
 for t in range(100,16001,tape["driver_interval"]):
  if t>100:advance(s,t)
  for key,value in schedule.get(t,[]):s.input(key,value)
  if t%500==0:
   s.cmd('tbreak *0xb076e');s.cmd('continue',timeout=60);ptr=rd(s,0x404);b=read_bytes(s,ptr,33600);(s.out/f'frame-{t}.bin').write_bytes(b)
   row=dict(field=field(s),input_field=t,hash=hashlib.sha256(b).hexdigest(),position=rd(s,0xa5d64),crash=read_bytes(s,0xa5dce,1).hex());rows.append(row);print(row,flush=True)
   if t in [500,4000,8000,12000,16000]:s.shot(f'scene-{t}.png')
 (s.out/'scenes.json').write_text(json.dumps(rows,indent=2))
finally:s.quit()
