#!/usr/bin/env python3
from pathlib import Path
import os,sys,json,signal,shutil,hashlib,struct,time,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1];os.chdir(root)
name=sys.argv[1];fields=int(os.environ.get('FIELDS','1000'));mode=os.environ.get('OBSERVE','survey');out=root/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True)
os.environ.update(SLAVE=os.environ.get('SLAVE',str(root/'tmp/build/release/FerrariFormulaOne.slave')),WARP='1',WINDOW='none',WHD_ARGS=os.environ.get('WHD_ARGS','CUSTOM1=0'),DETERMINISTIC='1',FSUAE=str(root/'tmp/step3/fs-uae'))
faultpc=None
s=Server('ff1measure',root=str(root),profile_window=False);log=[];result={'name':name,'protocol':'matched_completed_loops','extra_args':os.environ.get('EXTRA_ARGS','')}
try:
 g=s.boot()
 def cmd(c,timeout=60):
  try:v=g.cmd(c,timeout=timeout)
  except TimeoutError:
   for attempt in range(9):
    assert g.p.poll() is None
    os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),0)
    print(name,'waiting for the same live command',flush=True)
    try:
     v=g.read_until(g.sent,60).replace('(gdb) ','').strip();break
    except TimeoutError:
     if attempt==8:raise
  log.append(c+'\n'+v)
  if faultpc is not None and c=='continue' and 'Breakpoint' in v:
   pc=int(g.cmd('p/x $pc').split('=')[-1].strip(),16)
   if pc==faultpc:
    result['fault']={n:int(g.cmd(f'p/x *(unsigned int*){probe+sym(n)}').split('=')[-1].strip(),16) for n in ('error','ticks','velocity_records_count')}
    result['fault']['registers']=g.cmd('info registers')
    result['fault']['fine_steps']=int(g.cmd(f'p/x *(unsigned int*){probe+sym("fine_steps")}').split('=')[-1].strip(),16)
    result['fault']['heading_steps']=int(g.cmd(f'p/x *(unsigned int*){probe+sym("heading_steps")}').split('=')[-1].strip(),16)
    g.cmd(f'dump binary memory {out.relative_to(root)}/fault-memory.bin 0 0x80000')
    start=probe+sym('velocity_shadow');g.cmd(f'dump binary memory {out.relative_to(root)}/fault-shadow.bin {start} {start+96}')
    raise RuntimeError('velocity diagnostic fault '+str(result['fault']['error']))
  return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):cmd(f'dump binary memory tmp/step5/{name}/{label}.bin 0 0x80000')
 cmd('break *0x65606');cmd('ignore $bpnum 119');v=cmd('continue');assert 'Breakpoint' in v,v
 dump('update120');result['demo']=val('*(unsigned short*)0x1bee8');assert result['demo']==1
 result['warp_before']=cmd('monitor warp-status');assert result['warp_before']=='warp=1';cmd('monitor warp 0');cmd('ignore $bpnum 4');assert 'Breakpoint' in cmd('continue')
 dump('anchor');result['warp_after']=cmd('monitor warp-status');assert result['warp_after']=='warp=0'
 b=(out/'anchor.bin').read_bytes();assert b[0x65600:0x65606]==bytes.fromhex('4eb900067120'),b[0x65600:0x65606].hex()
 result['anchor_state']={n:struct.unpack_from('>H',b,a)[0] for n,a in [('demo',0x1bee8),('segment',0x6a60a),('speed',0x2275a),('countdown',0x66f94),('field_counter',0x24ad2)]}
 listing=Path(os.environ['SLAVE']).with_suffix('.list').read_text()
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
 probe=val('*(unsigned int*)0x654e8')-sym('barrier');faultpc=probe+sym('velocity_stop')
 cmd('delete');cmd(f'break *{faultpc}');cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
 dump('loop125')
 previous=125
 if os.environ.get('CONTACT')=='1':
  cmd('delete');cmd('break *0x6988c');cmd('break *0x69496');v=cmd('continue');assert 'Breakpoint' in v,v;assert val('$pc')==0x6988c,v
  dump('contact');result['contact_car']=val('*(unsigned short*)0x32fbc');assert result['contact_car']==0
  cmd('delete');cmd('break *0x65174');assert 'Breakpoint' in cmd('continue');dump('loop126');previous=126
 for tick in (150,175,225):
  cmd(f'ignore $bpnum {tick-previous-1}');assert 'Breakpoint' in cmd('continue');dump(f'loop{tick}');previous=tick
 listing=Path(os.environ['SLAVE']).with_suffix('.list').read_text()
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
 probe=val('*(unsigned int*)0x654e8')-sym('barrier')
 result['probe']={n:val(f'*(unsigned int*){probe+sym(n)}') for n in ('schedule_completed','installed','error','ticks','velocity_installed','velocity_loads','velocity_stores','velocity_rotations','velocity_projects','velocity_raws','velocity_records_count','velocity_cold_writes','velocity_swaps','velocity_work_resets','velocity_clamps','velocity_impulses','velocity_offroads','speed_records_count','speed_loads','speed_stores','speed_cold_writes','speed_swaps','bridge_installed','bridge_loads','bridge_stores','bridge_rotations','fine_installed','fine_steps','heading_installed','heading_steps','heading_zeroes','heading_resets','heading_assignments','steering_installed','steering_samples','steering_resets','wear_installed','wear_samples','wear_resets','events_installed','events_samples','events_rng_calls','events_pulses','clocks_installed','clocks_samples','counters_installed','counters_samples','fuel_installed','fuel_samples','fuel_resets','boost_samples','recovery_installed','recovery_contacts','recovery_samples')}
 assert result['probe']['installed']==1 and result['probe']['error']==0,result['probe']
 if name.endswith(('-bridge','-fine')):
  assert result['probe']['velocity_records_count']==(0 if os.environ.get('LEAN')=='1' else 800),result['probe']
  for label,size in [('schedule_context',56),('schedule_records',3200),('velocity_records',64000),('velocity_shadow',96),('velocity_target_speeds',3200),('speed_records',131072),('speed_shadow',48),('speed_feedback_records',6400),('position_shadow',96),('heading_shadow',96),('fine_records',25600),('heading_records',38400),('position_velocity_inputs',9600),('steering_shadow',144),('steering_records',16000),('wear_records',131072),('wear_remainders',24),('events_records',128000),('clocks_records',6400),('counters_records',6400),('fuel_records',131072),('fuel_remainders',16),('boost_records',4800),('recovery_contact_records',12800),('recovery_records',25600)]:
   if os.environ.get('LEAN')=='1' and label not in ('schedule_context','velocity_shadow','speed_shadow','position_shadow','heading_shadow','steering_shadow','wear_remainders','fuel_remainders'):continue
   start=probe+sym(label);cmd(f'dump binary memory tmp/step5/{name}/{label}.bin {start} {start+size}')
 result['slave_sha256']=hashlib.sha256(Path(os.environ['SLAVE']).read_bytes()).hexdigest()
 cmd(f'monitor census 1 "" "{out}/cache-check.jsonl"')
 result['cache_meta']=json.loads((out/'cache-check.jsonl').read_text().splitlines()[0])
 result['warp_end']=cmd('monitor warp-status');assert result['warp_end']=='warp=0'
 result['end_state']={n:val(f'*(unsigned short*){a}') for n,a in [('demo',0x1bee8),('segment',0x6a60a),('speed',0x2275a)]};assert result['end_state']['demo']==1
 for f in ('launch.json','fsuae.log'):shutil.copy(root/'amiga/.run'/f,out/f)
 result['emulator_sha256']=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest();result['status']='complete'
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,'complete',result['end_state'],flush=True)
except Exception as e:
 result['status']='failed';result['error']=repr(e);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');raise
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
