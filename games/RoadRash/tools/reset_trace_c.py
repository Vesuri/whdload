import sys,re,json
from harness_a import *
s=Session(sys.argv[1]);points=[]
try:
 route(s)
 target=rd(s,0x87480)
 text=(ROOT/'tmp/c-input-guard-build/RoadRash-verify.lst').read_text(encoding='latin1')
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',text,re.M)[1],16)
 base=target-sym('step_main');fail=base+sym('step_input_failed')
 s.cmd(f'break *{fail:#x}')
 s.cmd('monitor key 59 1');s.cmd('monitor fields 39');s.cmd('monitor key 59 0');s.cmd('monitor fields 99')
 for i in range(500):
  s.input('JOY2_FIRE_BUTTON',1);s.cmd('monitor fields 4');s.input('JOY2_FIRE_BUTTON',0);s.cmd('monitor fields 14')
  pc=int(re.search(r'pc\s+0x([0-9a-f]+)',s.cmd('info registers pc'))[1],16)
  if pc==fail:
   v=dict(field=field(s),stats=read_bytes(s,base+sym('step_stats'),24).hex(),queue=read_bytes(s,base+sym('step_queued_field'),8).hex(),hook=hex(rd(s,0xa5916)),stack=s.cmd('x/40wx $sp'),registers=s.cmd('info registers'));print(v,flush=True);(s.out/'failure.json').write_text(json.dumps(v,indent=2));break
 else:raise RuntimeError('no failure')
finally:s.quit()
