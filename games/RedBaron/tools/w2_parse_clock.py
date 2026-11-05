import json,re,sys
from pathlib import Path
import step_log,route_status as r
path=Path(sys.argv[1]);text=path.read_text();rows=[];active={};calls=[];unmatched=[]
skip=set(sys.argv[2:])
for name,kind,step,vbl,beam,ticks,sp in re.findall(r'RB_CLOCK (\w+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+)',text):
 if name in skip:continue
 row=dict(routine=name,kind=kind,step=int(step),vbl=int(vbl),beam=int(beam),ticks=int(ticks),sp=int(sp));row['line']=(row['beam']>>8)&511;row['hpos']=row['beam']&255;rows.append(row)
 if kind=='enter':
  assert name not in active,(name,active.get(name),row)
  active[name]=row
 elif name in active:
  first=active.pop(name);assert first['sp']==row['sp'],(name,first,row)
  calls.append(dict(routine=name,entry=first,return_record=row))
 else:unmatched.append(row)
state=r.read(r.locate());end=step_log.collect();stop=re.search(r'RB_CLOCK_STOP (\d+)',text)
phase=[dict(vbl=int(v),beam=int(b),line=(int(b)>>8)&511) for v,b in re.findall(r'RB_VBL (\d+) (\d+)',text)]
result=dict(complete=int(stop[1])==state['game_anchor'],rows=rows,calls=calls,open_calls=list(active.values()),unmatched_returns=unmatched,steps=end,vblank_phase=phase,excluded_routines=sorted(skip))
path.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');print(len(calls),'complete calls')
