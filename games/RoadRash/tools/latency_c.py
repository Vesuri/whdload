import os,sys,json,struct
from harness_a import *
os.environ['WHD_ARGS']=os.environ.get('WHD_ARGS','')+' CUSTOM2=1'
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1);advance(s,300);before=snapshot(s);s.input('JOY2_RIGHT',1);advance(s,360)
 target=rd(s,0x87738);data=read_bytes(s,target,1024);off=data.find(b'RRCLAT01');assert off>=0
 names=['input','replay_live','replay_tick','sim_live','sim_tick','render_live','render_tick','swap_enter','swap_return','front','steering','lateral','raw','debt']
 values=struct.unpack_from('>14I',data,off+8);trace=dict(zip(names,values))
 assert trace['input']>300 and trace['replay_tick']==trace['input'],trace
 assert trace['sim_tick']==trace['replay_tick'] and trace['render_tick']>=trace['sim_tick'],trace
 assert trace['input']<=trace['replay_live']<=trace['sim_live']<=trace['render_live']<=trace['swap_enter']<=trace['swap_return'],trace
 assert trace['steering']!=0 and trace['raw']&8 and trace['front'] in (0x6f780,0x77cc0),trace
 elapsed={name:20*(trace[name]-300) for name in ['input','replay_live','sim_live','render_live','swap_enter','swap_return']}
 result=dict(trace=trace,milliseconds_since_injection=elapsed,before=before,after=snapshot(s),provenance=provenance(os.environ['SLAVE'],s))
 if os.environ.get('RR_STACK_TEST'):
  from stack_probe_c import stack_probe
  result['stack']=stack_probe(s)
 (s.out/'latency.json').write_text(json.dumps(result,indent=2)+'\n');s.shot('steering.png');print(json.dumps(dict(trace=trace,milliseconds_since_injection=elapsed)),flush=True)
finally:s.quit()
