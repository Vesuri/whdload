import sys,re,json
from harness_a import *
lst=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',lst,re.M)[1],16)
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1);advance(s,1000)
 base=rd(s,0x8bdf2)-sym('step_actor_road_copy');entry=base+sym('step_steering_finish');history=base+sym('step_road_fraction')
 s.cmd(f'break *{entry:#x}')
 for _ in range(400):
  s.cmd('continue',timeout=60)
  if read_bytes(s,0xa5dce,1)[0]<128:break
 else:raise RuntimeError('crash not reached')
 before=read_bytes(s,history,12).hex();f=field(s)
 assert bytes.fromhex(before)!=bytes(12), 'need naturally nonzero history'
 ret=rd(s,rdreg:=int(re.search(r'\bsp\s+0x([0-9a-fA-F]+)',s.cmd('info registers sp'))[1],16))
 s.cmd('disable 1');s.cmd(f'tbreak *{ret:#x}');s.cmd('continue',timeout=60)
 after=read_bytes(s,history,12);assert after==bytes(12),after.hex()
 (s.out/'result.json').write_text(json.dumps(dict(field=f,before=before,injected=False,after=after.hex(),provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('crash history cleared',f,before,flush=True)
finally:s.quit()
