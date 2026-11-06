#!/usr/bin/env python3
"""Delta-copy coherence probe for plain TFX (pl_020): no external chip writer.

  tfx_delta_probe.py OUT

Env: MACHINE (default 030), DELTA_LISTING, PROFILE_SLAVE, FLIGHT_TAPE (inputs by swap,
as the profiles), SWAPS (default 400). At every swap request (TFX $018a6, the call to
do_swap_screen) it reads the page about to be published (logbase word, 0 or 4) and, if
that page's shadow is initialized (delta_seen), compares the chip destination
(old_bufs) with the fast shadow. Equal every time means only do_swap_screen wrote the
chip buffers, so copying only changed blocks is exact. Counts initialized and
uninitialized pages; a second @PlayLevel must clear the flags (reported, not required).
"""
import os,sys,re,json
from pathlib import Path
from replay_flight import ROOT,run,TAPE
from baseline_matrix import VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
machine=os.environ.get('MACHINE','030')
v=dict(VARIANTS['integer'],extra_args={'030':'--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true','020':'--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true','060':'--uae_fpu_no_unimplemented=true','040':'--uae_fpu_no_unimplemented=true'}[machine])
def capture(cmd,dump,bases,hs,out):
 base=bases[0];listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
 sym=lambda n:int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 sb=int.from_bytes(dump('swap-target.bin',base+v['swap']+2,4),'big')-sym('do_swap_screen')
 def scalar(n):
  cmd(f'monitor tfxsync {sb+sym(n):x} 4');return int.from_bytes(dump(n+'.bin',sb+sym(n),4),'big')
 shadow=scalar('delta_shadow');assert shadow,'no delta shadow allocated'
 assert dump('hook.bin',base+0x15ac,6)==bytes.fromhex('4ef9')+(sb+sym('reset_copy_shadows_tfx')).to_bytes(4,'big')
 logptr=scalar('_logbase_ptr');tape=json.loads(TAPE.read_text())
 cmd('delete breakpoints');cmd(f'break *{base+v["swap"]:#x}');swaps=1;checks=[];n=int(os.environ.get('SWAPS','400'))
 while swaps<=n:
  cmd('continue');swaps+=1
  for e in tape['flight_inputs']:
   if e['swap']==swaps:
    if 'key' in e:cmd(f"monitor key {e['key']:x} {e['value']}")
    else:cmd(f"monitor input {e['event']} {e['value']}")
  cmd(f'monitor tfxsync {logptr:x} 2');page=int.from_bytes(dump('page.bin',logptr,2),'big');assert page in (0,4),page
  cmd(f'monitor tfxsync {sb+sym("delta_seen"):x} 8');seen=dump('seen.bin',sb+sym('delta_seen')+page,1)[0]
  target=scalar('old_bufs')
  if seen:
   addr=shadow+(page//4)*64000;cmd(f'monitor tfxsync {addr:x} 64000')
   cached=dump('shadow.bin',addr,64000);actual=dump('chip.bin',target,64000)
   diff=sum(1 for a,b in zip(cached,actual) if a!=b)
   checks.append(dict(swap=swaps,page=page,equal=diff==0,bytes=diff))
   assert diff==0,('external chip writer',swaps,diff)
  else:checks.append(dict(swap=swaps,page=page,initialized=False))
 (out/'coherence.json').write_text(json.dumps(dict(swaps=n,compared=sum(1 for c in checks if 'equal' in c),checks=checks)))
 print('coherent',sum(1 for c in checks if c.get('equal')),'of',sum(1 for c in checks if 'equal' in c),'compared',flush=True)
run(machine,out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),capture,v)
