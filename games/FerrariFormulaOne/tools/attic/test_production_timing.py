from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='production-timing';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/production/FerrariFormulaOne.slave';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae-q03-final'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),profile_window=False);log=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=180);log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):
  limit=0x80000 if profile.startswith('a500') else 0x200000 if profile=='a1200' else 0x600000
  cmd(f'dump binary memory {out.relative_to(r)}/{label}.bin 0 {limit}')
  mem=(out/(label+'.bin')).read_bytes()
  if profile=='a500-fast':
   cmd(f'dump binary memory {out.relative_to(r)}/{label}-fast.bin 0x200000 0x400000')
   mem+=bytes(0x200000-len(mem))+(out/(label+'-fast.bin')).read_bytes()
  if profile.startswith('a500'):
   cmd(f'dump binary memory {out.relative_to(r)}/{label}-slow.bin 0xc00000 0xd80000')
   mem+=bytes(0xc00000-len(mem))+(out/(label+'-slow.bin')).read_bytes()
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
 cmd('monitor warp 0');cmd('ignore $bpnum 9');assert 'Breakpoint' in cmd('continue')
 def context():return [val(f'*(unsigned int*){ctx+i*4}') for i in range(14)]
 report['elapsed_start']=context();report['warp_start']=cmd('monitor warp-status');updates=300 if kind=='000' else 600 if kind=='020' else 3000
 cmd('ignore $bpnum '+str(updates-1));assert 'Breakpoint' in cmd('continue')
 report['elapsed_end']=context();report['warp_end']=cmd('monitor warp-status');x=report['elapsed_start'];y=report['elapsed_end']
 elapsed=(y[0]-x[0])*71051/3546895;simulated=(y[6]-x[6])*((y[7]&65535)/1000)
 report.update(elapsed_seconds=elapsed,simulated_seconds=simulated,error_percent=abs(simulated/elapsed-1)*100)
 assert report['error_percent']<=1 and simulated==60 and report['warp_start']==report['warp_end']=='warp=0',report
 listing=(b.parent/kind/'fine.list').read_text()
 import re
 pubs=[int(m[1],16)+6 for m in re.finditer(r'^00:([0-9A-F]{8}) 4EB90002A270\s+\d+:\s+jsr \$2a270',listing,re.M)]
 assert len(pubs)==1,pubs
 publication=probe+sy["B8_654fc"];cmd('delete');cmd(f'break *{publication}');assert 'Breakpoint' in cmd('continue')
 report['fps_start']=context();cmd('ignore $bpnum 299');assert 'Breakpoint' in cmd('continue');report['fps_end']=context()
 fields=report['fps_end'][0]-report['fps_start'][0];report['fps']=300/(fields*71051/3546895);report['fps_fields']=fields
 report['error']=val(f'*(unsigned int*){probe+sy["error"]}');report['status']='passed' if report['error']==0 and report['fps']>=(3.494 if kind=='000' else 5.54) else 'failed'
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True);assert report['status']=='passed'

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
