#!/usr/bin/env python3
"""Read-only W1 whole-call timing for cached CPUs, with live replacement endpoints."""
import argparse,json,re
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--entry',type=Path,required=True);p.add_argument('--mask',type=int,required=True);p.add_argument('--step',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
at=r.locate();state=r.read(at);obs,h=step_log.header();sim=state['sim'];remaining=a.step-state['game_steps'];listing=(a.entry/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
slave=at-label('tape_marker')
if remaining<=0:raise SystemExit('Target must be a later step')
mirror_ret=slave+label('mirror_fast_return') if a.mask&1 else sim+0x30570
routines=[('mirror',sim+0x304d0,[mirror_ret]),('draw',sim+0x30408,[sim+0x3045c]),('world3d',sim+0x2c552,[sim+0x2c806]),('world_step',sim+0x1098,[sim+0x11c8])]
if a.mask&2:
 lo,hi=label('cache_get'),label('cache_normalize_mask')
 rets=[slave+int(x,16) for x in re.findall(r'^00:([0-9A-Fa-f]+)\s+4E75\s+.*\brts\b',listing,re.M) if lo<=int(x,16)<hi]
 assert len(rets)==2
 routines.append(('cache_lookup',slave+lo,rets))
cmd=[f'break *{sim+0x2d34e:#x}','commands','silent',f'printf "RB_VBL %u %u\\n", *(unsigned long*){obs+36:#x}, *(unsigned long*)0xdff004','continue','end']
for name,entry,rets in routines:
 for tag,pc in [('enter',entry)]+[('return',ret) for ret in rets]:
  cmd += [f'break *{pc:#x}','commands','silent',f'printf "RB_CLOCK {name} {tag} %u %u %u %u %u\\n", *(unsigned long*){at+44:#x}, *(unsigned long*){obs+36:#x}, *(unsigned long*)0xdff004, *(unsigned long*){sim+0x30006:#x}, $sp']
  if tag=='enter' and name in ('draw','cache_lookup'):
   cmd += [f'printf "RB_INPUT {name} %u %u %u %u %u\\n", $a0, $d0, $d1, $d2, ($a0 ? *(unsigned long*)($a0+8) : 0)']
  cmd += ['continue','end']
if a.mask&2:
 build_pcs=[slave+int(x,16) for x in re.findall(r'^00:([0-9A-Fa-f]+)\s+.*\bbsr cache_drop\s*$',listing,re.M) if lo<=int(x,16)<hi]
 assert len(build_pcs)==1,build_pcs
 cmd += [f'break *{build_pcs[0]:#x}','commands','silent','printf "RB_CACHE_BUILD\\n"','continue','end']
cmd += [f'break *{state["game_anchor"]:#x}',f'ignore $bpnum {remaining-1}',f'break *{sim+0x21f4a:#x}','continue','printf "RB_CLOCK_STOP %u\\n", $pc','delete']
reply=r.command('gdb '+'\n'.join(cmd));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.with_suffix('.txt').write_text(reply+'\n');rows=[];active={};calls=[];incomplete=[]
for line in reply.splitlines():
 if line.strip()=='RB_CACHE_BUILD':
  assert 'cache_lookup' in active
  active['cache_lookup']['built']=True
  continue
 m=re.search(r'RB_INPUT (\w+) (\d+) (\d+) (\d+) (\d+) (\d+)',line)
 if m:
  name=m[1];assert name in active
  active[name].update(dict(zip(['a0','d0','d1','d2','dimensions'],map(int,m.groups()[1:]))));continue
 m=re.search(r'RB_CLOCK (\w+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+)',line)
 if not m:continue
 name,kind,step,vbl,beam,ticks,sp=m.groups();row=dict(routine=name,kind=kind,step=int(step),vbl=int(vbl),beam=int(beam),ticks=int(ticks),sp=int(sp));row['line']=(row['beam']>>8)&511;row['hpos']=row['beam']&255;rows.append(row)
 if kind=='enter':
  if name in active:raise RuntimeError('Nested or missing-return call')
  active[name]=row
 elif name in active:
  first=active.pop(name)
  if first['sp']!=row['sp']:raise RuntimeError('Return SP differs')
  calls.append(dict(routine=name,entry=first,return_record=row))
 else:incomplete.append(row)
end=step_log.collect();stop=re.search(r'RB_CLOCK_STOP (\d+)',reply);complete=bool(stop and int(stop[1])==state['game_anchor'] and end['count']==a.step)
phase=[dict(vbl=int(v),beam=int(b),line=(int(b)>>8)&511) for v,b in re.findall(r'RB_VBL (\d+) (\d+)',reply)]
if any(y['vbl']!=x['vbl']+1 for x,y in zip(phase,phase[1:])):raise RuntimeError('VBlank observer discontinuity')
result=dict(vblank_phase=phase,complete=complete,requested_step=a.step,mask=a.mask,routines=routines,rows=rows,calls=calls,open_calls=list(active.values()),unmatched_returns=incomplete,steps=end,scope='Inclusive wall time from entry to just before RTS; phase validation required; no CPU-cycle or FPS claim.')
a.out.write_text(json.dumps(result,indent=2)+'\n');print('complete',complete,'calls',len(calls))
if not complete:raise SystemExit('Requested flight checkpoint not reached')
