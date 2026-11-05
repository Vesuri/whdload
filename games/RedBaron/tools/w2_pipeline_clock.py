#!/usr/bin/env python3
"""Read-only W1 whole-call timing for cached CPUs, with live replacement endpoints."""
import argparse,json,re
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--group',choices=['draw','math','other','lines'],required=True);p.add_argument('--entry',type=Path,required=True);p.add_argument('--mask',type=int,required=True);p.add_argument('--step',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
at=r.locate();state=r.read(at);obs,h=step_log.header();sim=state['sim'];remaining=a.step-state['game_steps'];listing=(a.entry/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
slave=at-label('tape_marker')
if remaining<=0:raise SystemExit('Target must be a later step')
mirror_ret=slave+label('mirror_fast_return') if a.mask&1 else sim+0x30570
routines=[(name,sim+entry,[sim+x for x in rets]) for name,entry,rets in [
 ('world3d',0x2c552,[0x2c806]),('world_step',0x1098,[0x11c8]),
 ('transform32',0x38dcc,[0x38e00,0x38e7e]),('transform16',0x3abe2,[0x3acc8]),
 ('projection32',0x38e9c,[0x38eea]),('projection16',0x3acca,[0x3ad26]),
 ('radius',0x3b282,[0x3b2a6]),('dot',0x3b1fa,[0x3b280]),
 ('clip',0x39ecc,[0x39f5a]),('polygon',0x2f292,[0x2f268,0x2f27c,0x2f290,0x2f552]),
 ('line',0x2ea28,[0x2ec9c,0x2ecac,0x2ed56,0x2ee04,0x2ee5e,0x2ee62,0x2eebe,0x2eff8]),('rectangle',0x2fc68,[0x2fca4,0x2fdfe]),
 ('bitmap',0x30572,[0x305ce,0x307cc]),('overlay',0x2c144,[0x2c1fc,0x2c2b0])]]
assert a.mask==0
groups={'lines':{'world3d','line'},'draw':{'world3d','polygon','line','rectangle'},'math':{'world3d','transform32','transform16','projection32','projection16','dot','clip'},'other':{'world3d','world_step','bitmap','overlay','radius'}}
routines=[r for r in routines if r[0] in groups[a.group]]
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
  if first['sp']!=row['sp']:raise RuntimeError(f'Return SP differs: {name} {first} {row}')
  calls.append(dict(routine=name,entry=first,return_record=row))
 else:incomplete.append(row)
end=step_log.collect();stop=re.search(r'RB_CLOCK_STOP (\d+)',reply);complete=bool(stop and int(stop[1])==state['game_anchor'] and end['count']==a.step)
phase=[dict(vbl=int(v),beam=int(b),line=(int(b)>>8)&511) for v,b in re.findall(r'RB_VBL (\d+) (\d+)',reply)]
if any(y['vbl']!=x['vbl']+1 for x,y in zip(phase,phase[1:])):raise RuntimeError('VBlank observer discontinuity')
result=dict(vblank_phase=phase,complete=complete,requested_step=a.step,mask=a.mask,routines=routines,rows=rows,calls=calls,open_calls=list(active.values()),unmatched_returns=incomplete,steps=end,scope='Inclusive wall time from entry to just before RTS; phase validation required; no CPU-cycle or FPS claim.')
a.out.write_text(json.dumps(result,indent=2)+'\n');print('complete',complete,'calls',len(calls))
if not complete:raise SystemExit('Requested flight checkpoint not reached')
