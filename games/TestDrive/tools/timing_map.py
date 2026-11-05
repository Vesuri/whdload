#!/usr/bin/env python3
"""Phase-5 selected state definitions and static direct-writer inventory."""
import json,re
from pathlib import Path
from harness import ROOT
VARS={'vbl':(-31782,4),'road_left':(-29290,2),'road_right':(-29288,2),'traffic_lane_offsets':(-29524,24),'heading':(-22328,4),'grade':(-22324,2),'oncoming_speed':(-29418,20),'pos':(-22352,4),'speed':(-22360,4),'rpm':(-26340,4),'gear':(-26336,2),'ratio':(-26334,2),'throttle':(-26332,2),'step_displacement':(-22344,4),'steer':(-22356,4),'x':(-22376,4),'road_turn':(-26196,4),'heading_delta':(-26204,4),'yaw':(-26186,4),'neutral_steer':(-26182,4),'clutch':(-22786,2),'shift_draw_0':(-29900,1),'shift_draw_1':(-29899,1),'shift_desired':(-29902,2),'shift_ticks':(-23364,2),'police_seen':(-29320,2),'police_clock':(-29318,2),'police_stop':(-29322,2),'police_phase':(-29316,2),'radar_flag':(-29248,4),'event':(-22480,2),'chances':(-23352,2),'stage':(-23346,2),'gas_approach':(-29904,2),'stage_end':(-26234,2),'score_total':(-26350,4),'rng':(-25640,2),'frames':(-22312,4),'mode':(-22504,2),'menu_car':(-22500,2),'traffic_pos':(-29584,24),'traffic_speed':(-29548,24),'traffic_x':(-29500,24),'oncoming_pos':(-29452,20),'oncoming_x':(-29398,20)}
def decode(b):
 return {n:(int.from_bytes(b[0x7ffe+o:0x7ffe+o+sz],'big',signed=True) if sz<=4 else [int.from_bytes(b[0x7ffe+o+i:0x7ffe+o+i+4],'big',signed=True) for i in range(0,sz,4)]) for n,(o,sz) in VARS.items()}
def main():
 out=ROOT/'tmp/phase5';out.mkdir(exist_ok=True);writers={n:[] for n in VARS}
 for region,fn in [('root','root'),('h3','overlay3'),('h4','overlay4')]:
  for line in (ROOT/'tmp/phase2'/(fn+'.disasm')).read_text().splitlines():
   parts=line.split('\t')
   if len(parts)<3:continue
   ins=' '.join(parts[2:]);m=re.match(r'(?:move|addq|subq|addi|subi|add|sub|clr|and|andi|or|ori|eor|neg|not)\.([bwl]) (.*)',ins)
   if not m:continue
   dst=m[2].rsplit(',',1)[-1];ea=re.fullmatch(r'(-?\d+)\(a4\)',dst)
   if not ea:continue
   off=int(ea[1]);sz={'b':1,'w':2,'l':4}[m[1]]
   for n,(o,size) in VARS.items():
    if off<o+size and o<off+sz:writers[n].append(dict(pc=region+':'+parts[0].strip().rstrip(':'),instruction=ins))
 (out/'direct-writers.json').write_text(json.dumps(writers,indent=2)+'\n')
 for preset in ('a500','a1200'):
  p=out/(preset+'-fields/states')
  if not (p/'metadata.json').exists():continue
  states=[decode(f.read_bytes()) for f in sorted(p.glob('[0-9][0-9][0-9][0-9].bin'))]
  (out/(preset+'-states.json')).write_text(json.dumps(states,indent=2)+'\n')
  print(preset)
  for n in ['gear','clutch','rng','event','police_clock']:
   changes=[(i,s[n]) for i,s in enumerate(states) if i==0 or s[n]!=states[i-1][n]]
   print(n,changes[:60], 'count',len(changes))
  print('end', {k:states[-1][k] for k in ['vbl','pos','speed','gear','rng']})
if __name__=='__main__':main()
