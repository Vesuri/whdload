#!/usr/bin/env python3
import os,json,re,sys,struct
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();machine=sys.argv[2] if len(sys.argv)>2 else '040';os.chdir(ROOT)
def capture(cmd,dump,bases,hs,out):
 b=bases[0];cmd('delete breakpoints');dump('fire-hook.bin',b+0x4e080,38);firekey=dump('fire-key.bin',b+0x40f62,1)[0]-1;assert 0<=firekey<128
 markers={b+0x19fc:'swap',b+0x26fe6:'launch',b+0x27040:'launch-done',b+0x4e080:'synthesis',b+0x1a5d6:'fire-weapon',b+0x1a792:'fire-done'}
 for a in markers:cmd(f'break *{a:#x}')
 swaps=1;events=[]
 while swaps<35:
  reply=cmd('continue');m=re.search(r'Breakpoint \d+, (0x[0-9a-f]+)',reply);assert m,reply[-500:]
  pc=int(m[1],16);kind=markers[pc];cmd('maintenance flush register-cache')
  if kind=='swap':
   swaps+=1
   if swaps==2:cmd('monitor key 44 1')
   if swaps==3:cmd('monitor key 44 0')
   if swaps in [5,15]:cmd('monitor input JOY2_FIRE_BUTTON 1')
   if swaps in [7,17]:cmd('monitor input JOY2_FIRE_BUTTON 0')
   if swaps==25:cmd(f'monitor key {firekey:x} 1')
   if swaps==27:cmd(f'monitor key {firekey:x} 0')
  else:
   regs=cmd('info registers');(out/f'event-{len(events)}.txt').write_text(regs)
   missile=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a2'))[1],16) if kind=='launch-done' else None
   events.append(dict(kind=kind,swap=swaps,pc=hex(pc),missile=missile))
   print(kind,swaps,flush=True)
 (out/'events.json').write_text(json.dumps(events,indent=2))
 launches=[e for e in events if e['kind']=='launch-done']
 assert len({e['missile'] for e in launches})==len(launches), 'missile allocation reused inside short fixture'
 (out/'summary.json').write_text(json.dumps(dict(completed_launches=len(launches),missiles=[hex(e['missile']) for e in launches],swaps=[e['swap'] for e in launches]),indent=2))
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true' if machine=='040' else '')
v['custom4']=int(os.environ.get('CUSTOM4','18'))
run(machine,out,Path(os.environ['TEST_SEED']) if 'TEST_SEED' in os.environ else out.parent/(out.name+'-seed'),capture,v)
