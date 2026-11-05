# FR2 oracle run (FASTRAM_PLAN.md FR2): boot the tools/fr2_build.py oracle
# fixture, warp until FR2OracleFinished, dump FR2State and FR2Results.
#   fr2_run.py PROFILE        (030-50-bce, 040-40-bce)
# Output tmp/step5/fr2-oracle-PROFILE/{result.json,results.bin}.
from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1]
out=r/'tmp/step5'/('fr2-oracle-'+profile+os.environ.get('FR2_TAG',''));out.mkdir(parents=True,exist_ok=True)
b=Path(os.environ.get('FR2_BUILD',str(r/'tmp/build/fr2-oracle-normal')))/'FerrariFormulaOne.slave'
profiles=json.loads((r/'tmp/manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile])
os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1'),DETERMINISTIC='1',
 FSUAE=os.environ.get('RELEASE_FSUAE',str(r/'tmp/step5-frame-observer-build/fs-uae')),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'])
s=Server('ff1measure',root=str(r),run_script='tools/run.sh',run_dir='tmp/run/default/.run',profile_window=False);log=[];report={}
try:
 g=s.boot()
 def cmd(c,timeout=180):
  v=g.cmd(c,timeout=timeout);log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label,lo,hi):
  cmd(f'dump binary memory {out.relative_to(r)}/{label}.bin {lo} {hi}');return (out/(label+'.bin')).read_bytes()
 def full(label):
  mem=dump(label,0,int(os.environ['CHIP_KB'])*1024)
  size=int(os.environ['FAST_KB'])*1024
  return mem+bytes(0x200000-len(mem))+dump(label+'-fast',0x200000,0x200000+size)
 for boot_attempt in range(20):
  g.cont();time.sleep(1);g.stop()
  mem=full('memory');u=lambda a:struct.unpack_from('>I',mem,a)[0]
  hits=[];at=0
  while True:
   at=mem.find(b'FF1B7PUBLICROOT',at)
   if at<0:break
   root=u(at-4)*4+4
   if 0<root<len(mem) and mem[root:root+2]==bytes.fromhex('6000'):hits.append((at,root))
   at+=1
  if hits:break
 assert len(hits)==1,hits
 marker,root=hits[0]
 build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];module=build['payloads']['fine'];sy=module['symbols']
 host=marker-hs['FF1PublicMarker'];probe=host+module['offset']
 report.update(profile=profile,slave=str(b),slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest(),host=hex(host),probe=hex(probe),
  emulator=os.environ['FSUAE'],emulator_sha256=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest(),extra_args=os.environ.get('EXTRA_ARGS',''),cpu=os.environ['CPU'])
 cmd('delete')
 t0=time.time()
 cmd(f'break *{probe+sy["B8Draw"]}');assert 'Breakpoint' in cmd('continue',timeout=1800)
 report['first_draw_seconds']=round(time.time()-t0,1);print('first B8Draw',report['first_draw_seconds'],flush=True)
 if os.environ.get('FR2_DEBUG'):
  cmd('delete');cmd(f'break *{probe+sy["FR2Oracle"]}');print(cmd('continue',timeout=300)[-200:],flush=True)
  cmd('delete');cmd(f'break *{probe+sy["FR2OracleOut"]}')
  g.cont();time.sleep(40);g.stop()
  print('pc',hex(val('$pc')),flush=True);print(cmd('info registers'),flush=True)
  st=probe+sy['FR2State'];print('state',[hex(val(f'*(unsigned int*){st+4*i}')) for i in range(6)],flush=True)
  print({k:hex(probe+v) for k,v in sy.items() if k.startswith(('FR2','FastRender','FRB'))},flush=True)
  raise SystemExit(0)
 cmd('delete')
 for n in ['velocity_fault','schedule_bad']:
  if n in sy:cmd(f'break *{probe+sy[n]}')
 cmd(f'break *{host+hs["FF1WrongVersion"]}')
 n=(sy['FR2CasesEnd']-sy['FR2Cases'])//0x50
 st=probe+sy['FR2State']
 cmd(f'break *{probe+sy["FR2OracleOut"]}');cmd('set $fr2bp=$bpnum')
 while True:
  cmd('ignore $fr2bp 15');v=cmd('continue',timeout=1800)
  assert val('$pc')==probe+sy['FR2OracleOut'],(hex(val('$pc')),v)
  done=val(f'*(unsigned int*){st+8}');bad=val(f'*(unsigned int*){st+16}')
  print('cases',done,'of',n,'failing',bad,round(time.time()-t0),flush=True)
  if done>=n:break
 report['seconds']=round(time.time()-t0,1)
 assert val(f'*(unsigned int*){st+12}')==1,'finished flag'
 st=probe+sy['FR2State'];state=dump('state',st,st+24)
 chip,fast,nxt,fin,failing,run=struct.unpack('>6I',state)
 n=(sy['FR2CasesEnd']-sy['FR2Cases'])//0x50
 res=dump('results',probe+sy['FR2Results'],probe+sy['FR2Results']+12*n)
 report.update(chip_scratch=hex(chip),fast_scratch=hex(fast),cases=n,cases_run=run,failing=failing,error=val(f'*(unsigned int*){probe+sy["error"]}'))
 bad=[]
 for i in range(n):
  d,first,cw,rc=struct.unpack_from('>IiHH',res,12*i)
  if d or rc:bad.append(dict(index=i,bytes=d,first=first,chip=cw>>8,fast=cw&255,rc=rc))
 report['mismatches']=bad[:200];report['mismatch_count']=len(bad)
 report['status']='passed' if run==n and not bad and failing==0 and fast>=0x200000 and chip<0x200000 else 'failed'
 (out/'result.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='mismatches'},indent=1),flush=True)
finally:
 import shutil
 for artifact in ('launch.json','fsuae.log'):
  if (r/'tmp/run/default/.run'/artifact).exists():shutil.copy(r/'tmp/run/default/.run'/artifact,out/artifact)
 (out/'capture.log').write_text('\n'.join(log))
 if not (out/'result.json').exists() or report.get('status') is None:
  (out/'result.json').write_text(json.dumps(dict(report,status='error'),indent=1)+'\n')
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
