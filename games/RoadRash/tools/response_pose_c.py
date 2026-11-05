import re,json,sys,struct
from harness_a import *
s=Session(sys.argv[1]);sites={0x8b9aa:'player_after_steering',0x875c8:'render_start',0x87736:'swap_start',0x8773c:'swap_return',0x8a92c:'pose_selected'}
try:
 route(s);s.input('JOY2_UP',1);advance(s,300);initial=snapshot(s);s.input('JOY2_RIGHT',1)
 for pc in sites:s.cmd(f'break *{pc:#x}')
 rows=[]
 for _ in range(2000):
  s.cmd('continue',timeout=60);pc=int(re.search(r'pc\s+0x([0-9a-f]+)',s.cmd('info registers pc'))[1],16);b=read_bytes(s,0xa5d60,0x80)
  if pc==0x8a92c and int(re.search(r'a1\s+0x([0-9a-f]+)',s.cmd('info registers a1'))[1],16)!=0xa5d60:continue
  pose=int(re.search(r'd0\s+0x([0-9a-f]+)',s.cmd('info registers d0'))[1],16)&65535 if pc==0x8a92c else None
  rows.append(dict(pose=pose,thresholds=read_bytes(s,0xa7bfa,6).hex(),event=sites[pc],field=field(s),cursor=rd(s,0xa5d50),lateral=struct.unpack_from('>h',b)[0],heading=struct.unpack_from('>h',b,12)[0],relative=struct.unpack_from('>h',b,0x30)[0],lean=struct.unpack_from('>h',b,0x34)[0],steering=rd(s,0xa7262,2),raw=read_bytes(s,0xa598c,1).hex(),front=hex(rd(s,0x404)),back=hex(rd(s,0x408))))
  if rows[-1]['field']>=330:break
 else:raise RuntimeError('timeline did not finish')
 (s.out/'timeline.json').write_text(json.dumps(dict(initial=initial,rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print(json.dumps(rows),flush=True)
finally:s.quit()
