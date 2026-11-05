#!/usr/bin/env python3
"""Read-only whole-call beam/VBlank observations; costs include interrupt time."""
import argparse,json,re
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--step',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();at=r.locate();state=r.read(at);obs,h=step_log.header();sim=state['sim'];remaining=a.step-state['game_steps']
if remaining<=0:raise SystemExit('Target must be a later step')
cmd=[f'break *{sim+0x2d34e:#x}','commands','silent',f'printf "RB_VBL %u %u\\n", *(unsigned long*){obs+36:#x}, *(unsigned long*)0xdff004','continue','end']
for name,lo,hi in [('mirror',0x304d0,0x30570),('world3d',0x2c552,0x2c806),('world_step',0x1098,0x11c8)]:
 for tag,off in [('enter',lo),('return',hi)]:
  cmd += [f'break *{sim+off:#x}','commands','silent',f'printf "RB_CLOCK {name} {tag} %u %u %u %u %u\\n", *(unsigned long*){at+44:#x}, *(unsigned long*){obs+36:#x}, *(unsigned long*)0xdff004, *(unsigned long*){sim+0x30006:#x}, $sp','continue','end']
cmd += [f'break *{state["game_anchor"]:#x}',f'ignore $bpnum {remaining-1}',f'break *{sim+0x21f4a:#x}','continue','printf "RB_CLOCK_STOP %u\\n", $pc','delete']
reply=r.command('gdb '+'\n'.join(cmd));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.with_suffix('.txt').write_text(reply+'\n');rows=[];active={};calls=[];incomplete=[]
for name,kind,step,vbl,beam,ticks,sp in re.findall(r'RB_CLOCK (\w+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+)',reply):
 row=dict(routine=name,kind=kind,step=int(step),vbl=int(vbl),beam=int(beam),ticks=int(ticks),sp=int(sp));row['line']=(row['beam']>>8)&511;row['hpos']=row['beam']&255;rows.append(row)
 if kind=='enter':
  if name in active:raise RuntimeError('Nested or missing-return call')
  active[name]=row
 elif name in active:
  first=active.pop(name)
  if first['sp']!=row['sp']:raise RuntimeError('Return SP differs')
  slots=(row['vbl']-first['vbl'])*313*227+(row['line']-first['line'])*227+row['hpos']-first['hpos']
  calls.append(dict(routine=name,entry=first,return_record=row,wall_fields_before_rts=slots/(313*227),endpoints_outside_vblank=first['line']>=40 and row['line']>=40))
 else:incomplete.append(row)
end=step_log.collect();stop=re.search(r'RB_CLOCK_STOP (\d+)',reply);complete=bool(stop and int(stop[1])==state['game_anchor'] and end['count']==a.step)
phase=[dict(vbl=int(v),beam=int(b),line=(int(b)>>8)&511) for v,b in re.findall(r'RB_VBL (\d+) (\d+)',reply)]
if any(b['vbl']!=a['vbl']+1 for a,b in zip(phase,phase[1:])):raise RuntimeError('VBlank observer discontinuity')
result=dict(vblank_phase=phase,complete=complete,requested_step=a.step,rows=rows,calls=calls,open_calls=list(active.values()),unmatched_returns=incomplete,steps=end,scope='Wall time from routine entry to just before RTS; includes interrupts. No main-only CPU cycle claim. Endpoints near VBlank require independent phase validation.')
a.out.write_text(json.dumps(result,indent=2)+'\n');print('complete',complete,'calls',len(calls),'phase-clear',sum(c['endpoints_outside_vblank'] for c in calls))
if not complete:raise SystemExit('Requested flight checkpoint not reached')
