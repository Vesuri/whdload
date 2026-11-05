#!/usr/bin/env python3
"""Read-only swap breakpoints at sim:3154a, stopped at a chosen later flight step."""
import argparse,json,re
from pathlib import Path
import route_status as r
import step_log
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--step',type=int,required=True);p.add_argument('--out',required=True);a=p.parse_args()
at=r.locate();state=r.read(at);obs,h=step_log.header();sim=state['sim'];n=a.step-state['game_steps']
if n<=0:raise SystemExit('Target step must be later than the current step')
cmd=f'''gdb break *{sim+0x3154a:#x}
commands
silent
printf "RB_SWAP %u %u %u\\n", *(unsigned long *){obs+36:#x}, *(unsigned long *){sim+0x30006:#x}, *(unsigned long *)0xdff004
continue
end
break *{state['game_anchor']:#x}
ignore $bpnum {n-1}
break *{sim+0x21f4a:#x}
continue
printf "RB_STOP_PC %u\\n", $pc
delete'''
reply=r.command(cmd)
rows=[dict(vbl=int(v),ticks=int(t),beam=int(b)) for v,t,b in re.findall(r'RB_SWAP (\d+) (\d+) (\d+)',reply)]
result=dict(requested_step=a.step,swaps=rows,steps=step_log.collect(),debugger=reply)
stopped=re.search(r'RB_STOP_PC (\d+)',reply)
result['mission_ended']=bool(stopped and int(stopped[1])==sim+0x21f4a)
result['transport_error']=any(x in reply for x in ['Invalid hex digit','Remote communication error','Remote connection closed'])
result['complete']=result['steps']['records'][-1]['step']==a.step and not result['mission_ended'] and not result['transport_error']
Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
print(f'{len(rows)} swaps; stopped at step {result["steps"]["records"][-1]["step"]}')

if not result['complete']:raise SystemExit('INCOMPLETE: requested flight step not reached; trailing swaps may belong to debriefing')
