# Hi25 high-end profile: H5 build/fixture, warp to the 100th draw, eight non-warp
# draws, then HI25_FIELDS traced fields (default 30). 040/060 use the measurement
# emulator copy with the barto hook in the 040/060 cycle-exact loop.
from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='hi25-profile';variant=os.environ.get('C1_VARIANT','candidate');name=kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=Path(os.environ['H5_BUILD'])/'FerrariFormulaOne.slave';profiles=json.loads((r/'tmp/manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1'),DETERMINISTIC='1',FSUAE=os.environ.get('RELEASE_FSUAE',str(r/('tmp/step5-frame-observer-040prof-build/fs-uae' if profile[:3] in ('040','060') else 'tmp/step5-frame-observer-build/fs-uae'))),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
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
 report=dict(root=hex(root),table=hex(table),race=hex(race),marker=hex(marker),pc=val('$pc'),slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
 cmd('delete');cmd(f'break *{root+0x2e6}')
 cmd('condition $bpnum *(unsigned int*)$a3 == 0x22f30')
 assert 'Breakpoint' in cmd('continue')
 race=val('$d0+*(unsigned int*)($a3+28)')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')

 build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine';module=build['payloads'][kind];sy=module['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+module['offset']
 report['registers']=cmd('info registers');report['launch']=json.loads((r/'tmp/run/default/.run/launch.json').read_text());report['runtime_sha256']=hashlib.sha256(Path(os.environ['WHDLOAD_BINARY']).read_bytes()).hexdigest();report['extra_args']=os.environ.get('EXTRA_ARGS','');report['emulator_sha256']=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest()
 report.update(host=hex(host),probe=hex(probe),kind=kind,selection=val(f'*(unsigned int*){host+hs["FF1ProfileMode"]}'))
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 cmd('delete')
 faults=['FF1WrongVersion']
 for n in faults:cmd(f'break *{host+hs[n]}')
 for n in (['C1Fault','velocity_stop'] if kind=='000' else ['C1Fault'] if kind=='020' else ['velocity_fault','schedule_bad']):
  if n in sy:cmd(f'break *{probe+sy[n]}')
 checkpoint=probe+sy['FF1PresentationAfterTick' if kind=='fine' else 'C1Checkpoint'];cmd(f'break *{checkpoint}')
 assert 'Breakpoint' in cmd('continue')
 report['stop_pc']=hex(val('$pc'));report['error']=val(f'*(unsigned int*){probe+sy["error"]}')
 if val('$pc')!=checkpoint:
  report['regs']=cmd('info registers');dump('fault');(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');raise AssertionError(report)
 ctx=probe+sy['schedule_context' if kind=='fine' else 'C1Context'];report['context_address']=hex(ctx)
 # Fixed presentation-entry anchor; no guest state writes or diagnostic slave.
 cmd('delete');cmd(f'break *{probe+sy["B8Draw"]}');cmd('ignore $bpnum 99');assert 'Breakpoint' in cmd('continue')
 cmd('monitor warp 0');cmd('ignore $bpnum 7');assert 'Breakpoint' in cmd('continue')
 report['warp']=cmd('monitor warp-status');assert 'warp=0' in report['warp']
 from step5_b7_addresses import Addresses
 memory=dump('start');addresses=Addresses(memory,table)
 (out/'addresses.json').write_text(json.dumps(addresses.rows,indent=2)+'\n')
 (out/'canonical.bin').write_bytes(addresses.canonical_memory(memory))
 report['start_context']=[struct.unpack_from('>I',memory,ctx+4*i)[0] for i in range(14)]
 report['demo']=struct.unpack_from('>H',memory,addresses.map(0x1bee8))[0]
 report['slave']=str(b);report['symbols']=sy;report['host_symbols']=hs
 mode=os.environ.get('RENDER_CAPTURE','profile');report['mode']=mode
 cmd('delete');fields=int(os.environ.get('HI25_FIELDS','30'));report['fields']=fields;cmd(f'monitor {mode} {fields} "" "{out}/'+('detail.bin' if mode=='profile' else 'window.jsonl')+'"')
 memory=dump('end')
 report['end_context']=[struct.unpack_from('>I',memory,ctx+4*i)[0] for i in range(14)]
 report['error']=val(f'*(unsigned int*){probe+sy["error"]}');assert report['error']==0
 report['status']='passed';report['scope']='Hi25 high-end profile; traced PAL fields after 100 warp draws and eight non-warp draw entries. No game memory writes. All trace costs retained.'
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print('Captured',out,flush=True)

finally:
 import shutil
 for artifact in ('launch.json','fsuae.log'):
  if (r/'tmp/run/default/.run'/artifact).exists():shutil.copy(r/'tmp/run/default/.run'/artifact,out/artifact)
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
