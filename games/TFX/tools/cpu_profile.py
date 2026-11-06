#!/usr/bin/env python3
"""2,000-field profile on any machine and executable, with an optional run-time Gouraud switch.

  cpu_profile.py OUT

Env: MACHINE (020, 030, 040, 060; default 040), VARIANT (integer = TFX, newfpu = tfx.020;
default newfpu), FLIGHT_TAPE, END_FIELD (default 2002), TEST_SEED (reuse a seed so both
sides boot the same disk), DELTA_LISTING (slave listing), PROFILE=0 (publications only,
no per-PC profile), GOURAUD=old|new: before the window, point the executable's
@GouraudFill (TFX $6b8e0, C arguments; tfx.020 $4f840, inline stream) at the slave's
old chunky+c2p entry (gouraud_fill / gouraud_fill_new) or the run fill (gouraud_runs_c /
gouraud_runs). The live bytes must already be a JMP to one of them.
ROT=off: restore DoRotPt0's original delta handler entry.
MASK=off: restore _MaskSprite's original eight-call plane loop entry.
DELTA=off|on|none: clear (or require, or require absent) the delta-copy shadow pointer.
EXPECT_GOURAUD=new|game: assert @GouraudFill is the run fill's JMP or the executable's own bytes. Not a balanced
pair: same slave and seed, but no entry matching, so small differences are noise.
"""
import os,sys,re,json,shutil
from pathlib import Path
from baseline_matrix import ROOT,run,observer,VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
machine=os.environ.get('MACHINE','040');vname=os.environ.get('VARIANT','newfpu')
extra={'040':'--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true',
       '030':'--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true','020':'--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true',
       '060':'--uae_fpu_no_unimplemented=true'}[machine]
v=dict(VARIANTS[vname],extra_args=extra+' '+os.environ.get('EXTRA_UAE',''))
if os.environ.get('CUSTOM4'):v['custom4']=int(os.environ['CUSTOM4'])
if os.environ.get('CUSTOM5'):v['custom5']=int(os.environ['CUSTOM5'])
SITES={'integer':(0x6b8e0,'gouraud_fill','gouraud_runs_c'),'original':(0x6b8e0,'gouraud_fill','gouraud_runs_c'),'newfpu':(0x4f840,'gouraud_fill_new','gouraud_runs')}
def capture(cmd,dump,bases,hs,out):
 setup={}
 if os.environ.get('AUDIT_RENDER'):
  from exe_compare_audit import audit
  audit(cmd,dump,bases,hs,out,machine,v,os.environ['DELTA_LISTING'])
 if os.environ.get('EXPECT_GOURAUD'):
  # Placement check: new = the slave's run fill entry, game = the executable's own bytes.
  listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
  sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
  sb=int.from_bytes(dump('swap-target.bin',bases[0]+v['swap']+2,4),'big')-sym('do_swap_screen')
  site,old,new=SITES[vname];live=dump('gouraud-live.bin',bases[0]+site,6)
  want=bytes.fromhex('4ef9')+(sb+sym(new)).to_bytes(4,'big') if os.environ['EXPECT_GOURAUD']=='new' else hs[0]['bytes'][site:site+6]
  assert live==want,(live.hex(),want.hex());setup['expect']=dict(site=hex(site),live=live.hex(),mode=os.environ['EXPECT_GOURAUD'])
 if os.environ.get('GOURAUD'):
  listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
  sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
  sb=int.from_bytes(dump('swap-target.bin',bases[0]+v['swap']+2,4),'big')-sym('do_swap_screen')
  site,old,new=SITES[vname];jmp=lambda n:bytes.fromhex('4ef9')+(sb+sym(n)).to_bytes(4,'big')
  live=dump('gouraud-live.bin',bases[0]+site,6);assert live in (jmp(old),jmp(new)),live.hex()
  want=jmp(new if os.environ['GOURAUD']=='new' else old)
  cmd(f'monitor tfxmem {bases[0]+site:x} {want.hex()}');assert dump('gouraud-selected.bin',bases[0]+site,6)==want
  setup=dict(site=hex(site),live=live.hex(),selected=want.hex(),mode=os.environ['GOURAUD'])
 if os.environ.get('DELTA'):
  # DELTA=off: clear delta_shadow so do_swap_screen copies the whole buffer; on: require it.
  listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
  sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
  sb=int.from_bytes(dump('swap-target.bin',bases[0]+v['swap']+2,4),'big')-sym('do_swap_screen');a=sb+sym('delta_shadow')
  cmd(f'monitor tfxsync {a:x} 4');ptr=int.from_bytes(dump('delta-shadow.bin',a,4),'big')
  assert (ptr==0) if os.environ['DELTA']=='none' else ptr,('delta shadow',hex(ptr))
  if os.environ['DELTA']=='off':cmd(f'monitor tfxmem {a:x} 00000000');assert dump('delta-off.bin',a,4)==bytes(4)
  setup['delta']=dict(mode=os.environ['DELTA'],shadow=hex(ptr))
 if os.environ.get('MASK')=='off':
  # TFX _MaskSprite entry $4c858 back to MOVEQ #7,D0 / MOVE.L A1,abs (relocated high word of $4c982).
  import struct
  site={'integer':0x4c858,'newfpu':0x4e400}[vname];absol=site+0x12a
  live=dump('mask-live.bin',bases[0]+site,2);assert live==bytes.fromhex('4ef9'),live.hex()
  raw=bytes.fromhex('700723c9')+struct.pack('>I',bases[0]+absol)[:2]
  cmd(f'monitor tfxmem {bases[0]+site:x} {raw.hex()}');assert dump('mask-off.bin',bases[0]+site,8)==raw+struct.pack('>I',bases[0]+absol)[2:]
  setup['mask']='off'
 if os.environ.get('ROT')=='off':
  # DoRotPt0 delta entry back to MOVEM.W (A0)+,D0-D1 / MOVE.L D4,D3 (no relocation).
  site={'integer':0x5f570,'newfpu':0x59748}[vname];raw=bytes.fromhex('4c9800032604')
  live=dump('rot-live.bin',bases[0]+site,2);assert live==bytes.fromhex('4ef9'),live.hex()
  cmd(f'monitor tfxmem {bases[0]+site:x} {raw.hex()}');assert dump('rot-off.bin',bases[0]+site,6)==raw
  setup['rot']='off'
 (out/'cpu-setup.json').write_text(json.dumps(dict(machine=machine,variant=vname,extra=v['extra_args'],**setup),indent=2))
 prof=os.environ.get('PROFILE','1')!='0'
 def observed_dump(name,addr,size):
  if prof and name=='start-hunk0.bin':cmd(f'monitor tfxstart {bases[0]}')
  if prof and name=='end-hunk0.bin':cmd(f'monitor tfxsave {out}/profile.csv')
  return dump(name,addr,size)
 observer(v,end=int(os.environ.get('END_FIELD','2002')))(cmd,observed_dump,bases,hs,out)
 if prof:dump('chip.bin',0,0x200000);dump('fast.bin',0x40000000,0x2000000)
run(machine,out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),capture,v)
shutil.copy(__file__,out/Path(__file__).name)
