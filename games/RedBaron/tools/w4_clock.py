#!/usr/bin/env python3
"""Read-only whole-call beam/VBlank observations; costs include interrupt time."""
import argparse,json,re,struct
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--entry',type=Path,required=True);p.add_argument('--mask',type=int,required=True);p.add_argument('--step',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();at=r.locate();state=r.read(at);obs,h=step_log.header();sim=state['sim'];remaining=a.step-state['game_steps']
if remaining<=0:raise SystemExit('Target must be a later step')
m=json.loads((a.entry/'entry.json').read_text());listing=(a.entry/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
slave=m['entry']['game_anchor']-label('tape_game_anchor')
cmd=[f'break *{sim+0x2d34e:#x}','commands','silent',f'printf "RB_VBL %u %u\\n", *(unsigned long*){obs+36:#x}, *(unsigned long*)0xdff004','continue','end']
for name,lo,hi in [('rectangle',sim+0x2fc68,[sim+0x2fca4,sim+0x2fdfe]),('world3d',sim+0x2c552,[sim+0x2c806])]:
 for tag,off in [('enter',lo)]+[('return',pc) for pc in hi]:
  cmd += [f'break *{off:#x}','commands','silent',f'printf "RB_CLOCK {name} {tag} %u %u %u %u %u\\n", *(unsigned long*){at+44:#x}, *(unsigned long*){obs+36:#x}, *(unsigned long*)0xdff004, *(unsigned long*){sim+0x30006:#x}, $sp','continue','end']
  if name=='rectangle' and tag=='enter':
   cmd.insert(len(cmd)-2, f'printf "RB_FILL_META %u %u %u %u\\n", $d0, $d1, $d2, $d3')
cmd += [f'break *{state["game_anchor"]:#x}',f'ignore $bpnum {remaining-1}',f'break *{sim+0x21f4a:#x}','continue','printf "RB_CLOCK_STOP %u\\n", $pc','delete']
reply=r.command('gdb '+'\n'.join(cmd));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.with_suffix('.txt').write_text(reply+'\n');rows=[];active={};calls=[];incomplete=[]
fill_meta=iter([tuple(map(int,values)) for values in re.findall(r'RB_FILL_META (\d+) (\d+) (\d+) (\d+)',reply)])
for name,kind,step,vbl,beam,ticks,sp in re.findall(r'RB_CLOCK (\w+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+)',reply):
 row=dict(routine=name,kind=kind,step=int(step),vbl=int(vbl),beam=int(beam),ticks=int(ticks),sp=int(sp));row['line']=(row['beam']>>8)&511;row['hpos']=row['beam']&255;rows.append(row)
 if kind=='enter':
  if name=='rectangle':row.update(zip(('x','y','width','height'),[v&65535 for v in next(fill_meta)]))
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
