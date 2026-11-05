#!/usr/bin/env python3
"""Read-only census of objects reaching sim:39d30 after object culling."""
import argparse,json,re
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--step',type=int,required=True);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
if a.out.exists():raise ValueError('Output already exists')
at=r.locate();state=r.read(at);sim=state['sim'];n=a.step-state['game_steps']
if n<=0:raise ValueError('Target step must be later')
cmd=f'''gdb break *{sim+0x39d30:#x}
commands
silent
set $rb_obj=*(unsigned long *)($a5+8)
printf "RB_OBJECT %u %u %u %u %u\\n", *(unsigned long *){at+44:#x}, $rb_obj, *(unsigned char *)$rb_obj, *(unsigned short *)($rb_obj+2), *(unsigned long *)($rb_obj+30)
continue
end
break *{state['game_anchor']:#x}
ignore $bpnum {n-1}
break *{sim+0x21f4a:#x}
continue
printf "RB_SCENE_STOP %u\\n", $pc
delete'''
reply=r.command(cmd)
rows=[dict(zip(('step','object','flags','model','extra'),map(int,v))) for v in re.findall(r'RB_OBJECT (\d+) (\d+) (\d+) (\d+) (\d+)',reply)]
stop=re.search(r'RB_SCENE_STOP (\d+)',reply)
result=dict(start_step=state['game_steps'],requested_step=a.step,complete=bool(stop and int(stop[1])==state['game_anchor']),objects=rows,steps=step_log.collect(),debugger=reply)
a.out.write_text(json.dumps(result,indent=2)+'\n');print(len(rows),'post-cull objects; complete',result['complete'])
