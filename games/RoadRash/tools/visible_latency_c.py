import os,sys,json
from harness_a import *
from drive import barto
s=Session(sys.argv[1]);inject=int(os.environ.get('RR_INJECT','300'));right=int(os.environ.get('RR_RIGHT','1'));count=20
try:
 route(s);s.input('JOY2_UP',1);advance(s,inject)
 initial=snapshot(s);(s.out/'initial-player.bin').write_bytes(read_bytes(s,0xa5d60,0x80));s.input(os.environ.get('RR_STEER','JOY2_RIGHT'),right)
 p=s.out/'capture.bin';s.cmd(f'monitor profile {count} "" "{p}"',timeout=120)
 end=field(s);trace=barto.load(str(p));assert len(trace.fields)==count
 assert end==inject+count+1,(inject,end,count)
 for i,f in enumerate(trace.fields):
  assert f.shot
  (s.out/f'field-{inject+i+2}.png').write_bytes(f.shot)
 del trace
 if not os.environ.get('RR_KEEP_TRACE'):p.unlink()
 (s.out/'final-player.bin').write_bytes(read_bytes(s,0xa5d60,0x80))
 result=dict(injection=inject,right=right,first_capture_field=inject+2,last_capture_field=end,initial=initial,after=snapshot(s),provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'visible.json').write_text(json.dumps(result,indent=2));print('captured',inject+2,end,'right',right,flush=True)
finally:s.quit()
