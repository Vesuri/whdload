#!/usr/bin/env python3
"""Drive through native keys, using read-only telemetry to stay on the road."""
import json,sys
from pathlib import Path
from harness import ROOT,live_regions,dump
import native_input
native_input.LOG=ROOT/'tmp/phase5/input-actions.jsonl'
from native_input import key,fields,request
name=sys.argv[1];limit=int(sys.argv[2]);target_speed=float(sys.argv[3]) if len(sys.argv)>3 else 85
end_margin=float(sys.argv[4]) if len(sys.argv)>4 else 100
out=ROOT/'tmp/phase5'/name;out.mkdir(exist_ok=False)
_,regions=live_regions(out);db=regions['td-data'];held=set()
def hold(wanted):
 global held
 for k in sorted(held-wanted):key(k,False)
 for k in sorted(wanted-held):key(k,True)
 held=set(wanted)
def state():
 b=dump(out/'current-data.bin',db,db+0x32a4).read_bytes()
 def v(o,n=2):return int.from_bytes(b[0x7ffe+o:0x7ffe+o+n],'big',signed=True)
 traffic=[{'pos':v(o+4*i,4)/65536,'x':v(x+4*i),'oncoming':on,'index':i} for o,x,n,on in [(-29584,-29500,6,False),(-29452,-29398,5,True)] for i in range(n) if v(o+4*i,4)]
 return {'traffic':traffic,'police_clock':v(-29318),'police_stop':v(-29322),'mode':v(-22504),'car':v(-22500),'gear':v(-26336),'rpm':v(-26340),'speed':v(-22360,4)/65536,'pos':v(-22352,4)/65536,'x':v(-22376,4)/65536,'steer':v(-22356,4)/65536,'neutral':v(-26182,4)/65536,'event':v(-22480),'chances':v(-23352),'stage':v(-23346),'end':v(-26234),'left':v(-29290),'right':v(-29288)}
try:
 for i in range(limit):
  s=state();(out/'state.json').write_text(json.dumps(s,indent=2)+'\n')
  with (out/'states.jsonl').open('a') as f:f.write(json.dumps(dict(step=i,**s))+'\n')
  if i%20==0:print(i,{k:v for k,v in s.items() if k!='traffic'},flush=True);request('shot '+str(out/f'{i:04d}.png'))
  if s['mode']!=0 or s['event'] or s['police_clock']>0 or s['pos']>s['end']-end_margin:
   print('STOP event/end',s,flush=True);break
  wanted=set()
  near=[t for t in s['traffic'] if not t['oncoming'] and t['index']!=5 and -12<t['pos']-s['pos']<45]
  oncoming=[t for t in s['traffic'] if t['oncoming'] and -8<t['pos']-s['pos']<65]
  lane=-100 if near and not oncoming else 100
  blocked=bool(near and oncoming and min(t['pos']-s['pos'] for t in near)<25)
  desired=max(-20,min(20,s['neutral']+(lane-s['x'])*.16))
  if s['steer']<desired-.6:wanted.add(0x4e)
  elif s['steer']>desired+.6:wanted.add(0x4f)
  speed_goal=25 if blocked else target_speed
  if s['speed']<speed_goal:wanted.add(0x4c)
  elif s['speed']>speed_goal+4:wanted.add(0x4d)
  if s['gear']>1 and s['rpm']<1800 and s['speed']<35:
   wanted.discard(0x4c);wanted.update((0x4d,0x40))
  elif s['gear']==0 or (s['rpm']>5200 and s['gear']<4):
   wanted.discard(0x4d);wanted.update((0x4c,0x40))
  if 0x40 in wanted and i%6>=3:wanted.discard(0x40)
  hold(wanted);fields(5)
finally:
 hold(set());fields(2)
 request('shot '+str(out/'end.png'));print(state(),flush=True)
