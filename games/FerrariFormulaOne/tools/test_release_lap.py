from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='release-lap';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=Path(os.environ.get('FF1_BUILD',str(r/'tmp/build/production')))/'FerrariFormulaOne.slave';profiles=json.loads((r/'tmp/manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1 ConfigDelay=0'),DETERMINISTIC=os.environ.get('FF1_DETERMINISTIC','1'),FSUAE=os.environ.get('RELEASE_FSUAE',str(r/'tmp/step5-frame-observer-build/fs-uae')),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),run_script='tools/run.sh',run_dir='tmp/run/default/.run',profile_window=False);log=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=180);log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):
  chip=int(os.environ['CHIP_KB'])*1024
  cmd(f'dump binary memory {out.relative_to(r)}/{label}.bin 0 {chip}')
  mem=(out/(label+'.bin')).read_bytes()
  for bank,base,key in [('fast',0x200000,'FAST_KB'),('slow',0xc00000,'SLOW_KB')]:
   size=int(os.environ[key])*1024
   if size:
    cmd(f'dump binary memory {out.relative_to(r)}/{label}-{bank}.bin {base} {base+size}')
    mem+=bytes(base-len(mem))+(out/(label+'-'+bank+'.bin')).read_bytes()
  return mem
 for boot_attempt in range(20):
  g.cont();time.sleep(1);g.stop()
  mem=dump('memory');u=lambda a:struct.unpack_from('>I',mem,a)[0]
  hits=[];at=0
  while True:
   at=mem.find(b'FF1B7PUBLICROOT',at)
   if at<0:break
   root=u(at-4)*4+4
   if 0<root<len(mem) and mem[root:root+2]==bytes.fromhex('6000'):hits.append((at,root))
   at+=1
  if hits:break
 assert len(hits)==1,hits
 marker,root=hits[0];table=u(root+16)*4;race=u(table+160*4)*4+4
 report=dict(profile=profile,launch=json.loads((r/'tmp/run/default/.run/launch.json').read_text()),runtime_sha256=hashlib.sha256(Path(os.environ['WHDLOAD_BINARY']).read_bytes()).hexdigest(),root=hex(root),table=hex(table),race=hex(race),marker=hex(marker),pc=val('$pc'),slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
 cmd('delete');cmd(f'break *{root+0x2e6}')
 cmd('condition $bpnum *(unsigned int*)$a3 == 0x22f30')
 assert 'Breakpoint' in cmd('continue')
 race=val('$d0+*(unsigned int*)($a3+28)')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')

 build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine';module=build['payloads'][kind];sy=module['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+module['offset']
 report.update(host=hex(host),probe=hex(probe),kind=kind,selection=val(f'*(unsigned int*){host+hs["FF1ProfileMode"]}'))
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 cmd('delete')
 faults=['FF1WrongVersion']
 for n in faults:cmd(f'break *{host+hs[n]}')
 for n in (['C1Fault','velocity_stop'] if kind=='000' else ['C1Fault'] if kind=='020' else ['velocity_fault','schedule_bad']):
  if n in sy:cmd(f'break *{probe+sy[n]}')
 checkpoint=probe+sy['schedule_end' if kind=='fine' else 'C1Checkpoint'];cmd(f'break *{checkpoint}')
 assert 'Breakpoint' in cmd('continue')
 report['stop_pc']=hex(val('$pc'));report['error']=val(f'*(unsigned int*){probe+sy["error"]}')
 if val('$pc')!=checkpoint:
  report['regs']=cmd('info registers');dump('fault');(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');raise AssertionError(report)
 ctx=probe+sy['schedule_context' if kind=='fine' else 'C1Context'];report['context_address']=hex(ctx)
 from step5_b7_addresses import Addresses
 memory=dump('lap-start');addresses=Addresses(memory,table);native=addresses.map
 report['lap_count_before']=val(f'*(unsigned short*){native(0x1bdea)}')
 report['segment_before']=val(f'*(unsigned short*){native(0x6a60a)}')
 report['context_before']=[val(f'*(unsigned int*){ctx+i*4}') for i in range(14)]
 cmd('delete');cmd(f'break *{native(0x67d5e)}');cmd(f'condition $bpnum *(unsigned short*){native(0x32fbc)} == 0')
 assert 'Breakpoint' in cmd('continue')
 report['native_count_suppression']=val(f'*(unsigned short*){native(0x1ed2c)}')
 report['lap_count_before_native_branch']=val(f'*(unsigned short*){native(0x1bdea)}')
 report['native_count_rule']='At $67d5e nonzero $1ed2c branches directly to $67df8, skipping the player lap-count increment at $67dea.'
 cmd('delete');cmd(f'break *{native(0x67e1e)}');cmd(f'condition $bpnum *(unsigned short*){native(0x32fbc)} == 0')
 assert 'Breakpoint' in cmd('continue')
 report['lap_time_native']=val(f'*(unsigned short*){native(0x22398)}');assert report['lap_time_native']>0
 report['lap_count_at_crossing']=val(f'*(unsigned short*){native(0x1bdea)}')
 cmd('delete');cmd(f'break *{checkpoint}');assert 'Breakpoint' in cmd('continue')
 report['last_lap_time']=val(f'*(unsigned short*){native(0x225d0)}');report['lap_time_after']=val(f'*(unsigned short*){native(0x22398)}')
 report['context_after']=[val(f'*(unsigned int*){ctx+i*4}') for i in range(14)]
 report['error']=val(f'*(unsigned int*){probe+sy["error"]}')
 assert report['last_lap_time']==report['lap_time_native'] and report['lap_time_after']<=2 and report['error']==0
 assert report['lap_count_at_crossing']==report['lap_count_before_native_branch']+(report['native_count_suppression']==0)
 report['status']='passed';dump('lap-complete');(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)

except Exception as e:
 report=locals().get('report',{});report.update(status='failed',exception=repr(e));(out/'result.json').write_text(json.dumps(report,indent=2));raise
finally:
 import shutil
 for f in ('launch.json','fsuae.log'):
  if (r/'tmp/run/default/.run'/f).exists():shutil.copy(r/'tmp/run/default/.run'/f,out/f)
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
