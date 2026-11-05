from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='h5-oracle';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=Path(os.environ['H5_BUILD'])/'FerrariFormulaOne.slave';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1'),DETERMINISTIC='1',FSUAE=os.environ.get('RELEASE_FSUAE',str(r/'tmp/step5-frame-observer-build/fs-uae')),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),profile_window=False);log=[]
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
 report['registers']=cmd('info registers');report['launch']=json.loads((r/'amiga/.run/launch.json').read_text());report['runtime_sha256']=hashlib.sha256(Path(os.environ['WHDLOAD_BINARY']).read_bytes()).hexdigest();report['extra_args']=os.environ.get('EXTRA_ARGS','');report['emulator_sha256']=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest()
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

 cmd('delete');cmd(f'break *{probe+sy["H5OracleDone"]}');cmd(f'break *{probe+sy["H5OracleBad"]}');assert 'Breakpoint' in cmd('continue')
 report['checked']=val(f'*(unsigned int*){probe+sy["H5OracleChecked"]}');report['oracle_error']=val(f'*(unsigned int*){probe+sy["H5OracleError"]}')
 assert val('$pc')==probe+sy['H5OracleDone'] and report['checked']==len(json.loads((b.parent/'cases.json').read_text())) and report['oracle_error']==0,report
 cmd('monitor warp 0');cmd('delete');cmd(f'break *{probe+sy["H5BenchStart"]}');assert 'Breakpoint' in cmd('continue')
 report['warp_start']=cmd('monitor warp-status');assert report['warp_start']=='warp=0'
 from step5_b7_addresses import Addresses
 memory=dump('benchmark-start');addresses=Addresses(memory,table);bitmap=addresses.map(0x24ae0);entry=memory[bitmap:bitmap+6]
 benchmode=val(f'*(unsigned short*){probe+sy["H5OracleBenchMode"]}')
 expected=bytes.fromhex('4ef9')+struct.pack('>I',probe+sy['FF1RenderBitmap']) if benchmode else bytes.fromhex('4a79')+struct.pack('>I',addresses.map(0x1c1b4))
 assert entry==expected,(entry.hex(),expected.hex());report['benchmark_entry']=entry.hex();report['original_entry_control_verified']=not bool(benchmode);report['field_start']=val(f'*(unsigned int*){ctx}')
 cmd('delete');cmd(f'break *{probe+sy["H5BenchDone"]}');assert 'Breakpoint' in cmd('continue')
 report['field_end']=val(f'*(unsigned int*){ctx}');report['warp_end']=cmd('monitor warp-status');report['mode']=val(f'*(unsigned short*){probe+sy["H5OracleBenchMode"]}')
 report['benchmark_calls']=20000;report['elapsed_seconds']=(report['field_end']-report['field_start'])*71051/3546895;report['us_per_glyph']=report['elapsed_seconds']/20000*1e6;report['resolution_us_per_glyph']=71051/3546895/20000*1e6
 assert report['warp_end']=='warp=0'
 report['status']='passed';(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)

finally:
 import shutil
 for artifact in ('launch.json','fsuae.log'):
  if (r/'amiga/.run'/artifact).exists():shutil.copy(r/'amiga/.run'/artifact,out/artifact)
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
