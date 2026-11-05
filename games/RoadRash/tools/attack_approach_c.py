"""Observe geometric NPC attack tests without changing simulation state."""
import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
 start=int(os.environ.get('RR_CHOICE_START','400'));end=int(os.environ.get('RR_CHOICE_END','1200'))
 for target,event,value in tape['events']:
  if target>start:break
  advance(s,target);s.input(event,value)
 advance(s,start)
 # No input changes are allowed inside the observed interval.
 assert not any(start<t<end for t,_,_ in tape['events'])
 s.cmd('break *0x90670');s.cmd('condition 1 $a1 == 0xa6260')
 s.cmd('break *0x8747e');s.cmd(f'condition 2 *(unsigned int*)0xa5d4c >= {end}')
 rows=[]
 for _ in range(2000):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc d0 a1')
  v={k:int(x,16) for k,x in re.findall(r'\b(pc|d0|a1)\s+0x([0-9a-fA-F]+)',regs)}
  if v['pc']==0x8747e:break
  rows.append(dict(field=field(s),cursor=rd(s,0xa5d50),subject_table=read_bytes(s,rd(s,0xa591c),16).hex(),player=read_bytes(s,0xa5d60,128).hex(),delta=rd(s,0xa6f00,2),subject=read_bytes(s,0xa6260,128).hex()))
 else:raise RuntimeError('choice probe limit')
 (s.out/'result.json').write_text(json.dumps(dict(start=start,end=end,rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n')
 print('approach checks',len(rows),flush=True)
finally:s.quit()
