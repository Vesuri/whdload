import re,sys,json,struct
from harness_a import *
lst=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',lst,re.M)[1],16)
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1)
 entry=rd(s,0x8bdf2);table=entry+sym('step_actor_road_fraction')-sym('step_actor_road_copy')
 s.cmd('break *0x87040');s.cmd(f'break *{entry:#x}');rows=[]
 def regs():return {k:int(v,16) for k,v in re.findall(r'\b(pc|sp|d0|d1|d2|a0|a1|a2)\s+0x([0-9a-fA-F]+)',s.cmd('info registers pc sp d0 d1 d2 a0 a1 a2'))}
 def carry(ptr):return rd(s,table+(ptr-0xa5d60)//32) if 0xa5d60<=ptr<0xa6ee0 and (ptr-0xa5d60)%128==0 else None
 for _ in range(2000):
  s.cmd('continue',timeout=60);before=regs();f=field(s)
  if before['pc']==entry:
   source=carry(before['a1']);dest=carry(before['a0']);original_source=source
   injected=bool(os.environ.get('RR_INJECT_CARRY')) and source is not None and dest is not None and before['a1']!=before['a0']
   if injected:
    s.cmd(f"set {{unsigned int}}{table+(before['a1']-0xa5d60)//32:#x}=3");source=3
    s.cmd(f"set {{unsigned int}}{table+(before['a0']-0xa5d60)//32:#x}=1")
   assert not injected or (carry(before['a1'])==3 and carry(before['a0'])==1),(carry(before['a1']),carry(before['a0']))
   ret=rd(s,before['sp']);s.cmd('disable 1 2');s.cmd(f'tbreak *{ret:#x}');s.cmd('continue',timeout=60);after=regs();assert after['pc']==ret
   for k in ['d0','d1','d2','a0','a1','a2']:assert before[k]==after[k],k
   result=carry(after['a0'])
   if injected:print('copy detail',hex(table),before,after,source,result,flush=True)
   if dest is not None:assert result==(source if source is not None else 0),(source,dest,result)
   if injected:
    s.cmd(f"set {{unsigned int}}{table+(before['a1']-0xa5d60)//32:#x}={original_source}")
    s.cmd(f"set {{unsigned int}}{table+(before['a0']-0xa5d60)//32:#x}={original_source}")
   rows.append(dict(injected=injected,field=f,source=hex(before['a1']),destination=hex(before['a0']),source_carry=source,old_destination=dest,new_destination=result))
   s.cmd('enable 1 2')
  if f>=int(os.environ.get("RR_COPY_FIELDS","1400")) or len(rows)>=40:break
 assert rows
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('validated copies',len(rows),'nonzero',sum(bool(r['source_carry']) for r in rows),flush=True)
finally:s.quit()
