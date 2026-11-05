import sys,json,os,re
from harness_a import *
s=Session(sys.argv[1])
try:
 for attempt in range(500):
  try:hook=rd(s,0xa5916)
  except (ValueError,IndexError):hook=0
  if hook==0x87040:break
  s.input('JOY2_FIRE_BUTTON',1);s.cmd('monitor fields 4',timeout=60)
  s.input('JOY2_FIRE_BUTTON',0);s.cmd('monitor fields 14',timeout=60)
 else:raise RuntimeError('race not reached')
 initial_field=field(s);assert initial_field<40,initial_field
 isc=rd(s,0x8747e,2)==0x4ef9
 end=rd(s,0x875b8) if isc else 0x875b6
 s.cmd(f'break *{end:#x}');s.cmd('break *0x8f57a')
 rows=[]
 for _ in range(200):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc');pc=int(re.search(r'pc\s+0x([0-9a-fA-F]+)',regs)[1],16)
  assert pc in [end,0x8f57a],hex(pc)
  r=dict(kind='release' if pc==0x8f57a else 'motion',live=field(s),cursor=rd(s,0xa5d50),delta=rd(s,0xa6f00,2),active=rd(s,0xa59d4,2),actors={hex(a):read_bytes(s,a,128).hex() for a in [0xa5d60,0xa61e0,0xa6260]})
  rows.append(r)
  if r['cursor']>=100:break
 else:raise RuntimeError('motion trace limit')
 result=dict(initial_field=initial_field,rows=rows,provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('early rows',len(rows),'release',[(r['live'],r['cursor'],r['delta']) for r in rows if r['kind']=='release'],flush=True)
finally:s.quit()
