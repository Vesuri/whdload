import json,os,re,sys,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1)
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
 base=rd(s,0x87480)-sym('step_main')
 npc=base+sym('step_npc_lateral_fraction');road=base+sym('step_actor_road_fraction')
 s.cmd('break *0x90c64');s.cmd('break *0x90c6a');s.cmd('break *0x8747e');s.cmd('condition 3 *(unsigned int*)0xa5d4c >= 3000')
 rows=[];pending=None
 for _ in range(300):
  s.cmd('continue',timeout=60)
  regs=s.cmd('info registers');v={k:int(x,16) for k,x in re.findall(r'\b(d[0-7]|a[0-7]|sp|pc|sr)\s+0x([0-9a-fA-F]+)',regs)}
  if v['pc']==0x8747e:break
  actor=v['a1'];assert 0xa5d60<=actor<0xa6ee0 and (actor-0xa5d60)%128==0
  offset=(actor-0xa5d60)//32
  state=dict(actor=hex(actor),field=field(s),cursor=rd(s,0xa5d50),npc=rd(s,npc+offset),road=rd(s,road+offset),registers=v)
  if v['pc']==0x90c64:
   assert pending is None;pending=state
  else:
   assert pending and pending['actor']==state['actor'];assert state['npc']==state['road']==0
   for k,val in pending['registers'].items():
    if k not in ['a4','pc']:assert v[k]==val,(k,val,v[k])
   assert v['a4']==0xa851a
   rows.append(dict(before=pending,after=state));pending=None
 else:raise RuntimeError('reactivation probe limit')
 assert pending is None and rows,'no complete reactivation observed'
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n')
 print('reactivations',len(rows),'nonzero prior carry',sum(bool(r['before']['npc'] or r['before']['road']) for r in rows),flush=True)
finally:s.quit()
