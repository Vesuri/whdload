import os,sys,json,struct
from harness_a import *
# C experiments explicitly opt into the public master switch.
if not any(x.upper().startswith("CUSTOM2=") for x in os.environ.get("WHD_ARGS", "").split()):
 os.environ["WHD_ARGS"] = os.environ.get("WHD_ARGS", "") + " CUSTOM2=1"
s=Session(sys.argv[1]);points=[]
try:
 s.cmd("monitor fields 999",timeout=120)
 s.press("JOY2_FIRE_BUTTON")
 for i in range(60):
  s.cmd('monitor fields 199',timeout=120)
  try:hook=rd(s,0xa5916);demo=rd(s,0xa7204,2)
  except (ValueError,IndexError):continue
  if hook==0x87040 and demo:break
 else:
  s.shot('no-demo.png');raise RuntimeError('no demo after intro and 12000 fields')
 for i in range(4):
  points.append(dict(field=field(s),demo=rd(s,0xa7204,2),timeout=rd(s,0xa7206,2),hook=rd(s,0xa5916),position=rd(s,0xa5d64)))
  s.cmd('monitor fields 99',timeout=120)
 s.shot('demo.png')
 if os.environ.get('RR_DEMO_TIMEOUT'):
  for i in range(40):
   s.cmd('monitor fields 99',timeout=120)
   if rd(s,0xa5916)!=0x87040:break
  else:raise RuntimeError('demo timeout did not exit')
 else:
  s.input('JOY2_FIRE_BUTTON',1);s.cmd('monitor fields 9',timeout=120);s.input('JOY2_FIRE_BUTTON',0)
 exit_state=dict(hook=rd(s,0xa5916),exit=rd(s,0xa59d2,2),demo_timer=rd(s,0xa7206,2),field=field(s))
 if os.environ.get('RR_DEMO_TIMEOUT'):assert exit_state['field']==3600-(points[0]['timeout']-points[0]['field']),exit_state
 assert exit_state['hook']!=0x87040,exit_state
 normal=route(s)
 assert rd(s,0xa7204,2)==0
 result=dict(points=points,exit_state=exit_state,normal=normal,provenance=provenance(os.environ['SLAVE'],s))
 if os.environ.get('RR_STACK_TEST'):
  from stack_probe_c import stack_probe
  result['stack']=stack_probe(s)
 (s.out/'demo.json').write_text(json.dumps(result,indent=2)+'\n');s.shot('after-demo-race.png');print(json.dumps(result),flush=True)
finally:s.quit()
