import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 tape=json.loads((ROOT/'tools/fixtures/c-attacks.json').read_text())
 for target,event,value in tape['events']:
  if target>1200:break
  advance(s,target);s.input(event,value)
 advance(s,1200)
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 sy={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)$',listing,re.M)}
 base=rd(s,0x87480)-sy['step_main']
 sites=[0x87486,0x87518,0x87530,0x87574,0x8757a,0x87580,0x87586,0x8758c,0x87592,0x87598,0x875b6]+[base+sy[n] for n in ['step_end','step_track_events','step_actor_animations','step_spark_events','step_scenery_cursor','step_pose_events','step_steering_finish']]+[0x8f552,0x8eff8]
 for i,pc in enumerate(sites,1):
  s.cmd(f'break *{pc:#x}');s.cmd(f'condition {i} *(unsigned int*)0xa5d50 == 1239')
 rows=[]
 for _ in sites:
  s.cmd('continue',timeout=60)
  regs=s.cmd('info registers pc')
  rows.append(dict(pc=regs,actor=read_bytes(s,0xa5d60,0x1180).hex(),cursor=rd(s,0xa5d50)))
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2))
 print('cursors',[r['cursor'] for r in rows],flush=True)
finally:s.quit()
