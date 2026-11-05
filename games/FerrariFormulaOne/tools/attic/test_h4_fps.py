from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='h4-fps';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=Path(os.environ['H4_BUILD'])/'FerrariFormulaOne.slave';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1'),DETERMINISTIC='1',FSUAE=os.environ.get('RELEASE_FSUAE',str(r/'tmp/step5-frame-observer-build/fs-uae')),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
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
 cmd('monitor warp 0')
 def context():return [val(f'*(unsigned int*){ctx+i*4}') for i in range(14)]
 listing=(b.parent/kind/'fine.list').read_text()
 import re
 pubs=[int(m[1],16)+6 for m in re.finditer(r'^00:([0-9A-F]{8}) 4EB90002A270\s+\d+:\s+jsr \$2a270',listing,re.M)]
 assert len(pubs)==1,pubs
 publication=probe+sy["B8_654fc"];cmd('delete');cmd(f'break *{publication}');cmd('ignore $bpnum 99');assert 'Breakpoint' in cmd('continue')
 report['fps_start']=context();cmd('delete');rows=[];meta=None;intervals=[]
 # Observe actual displayed-buffer changes without 300 debugger round trips.
 # Keep the first 300 complete intervals, excluding both window edges.
 for capture_fields in [2000,1000]:
  path=out/f'census-{len(rows)}.jsonl';cmd(f'monitor census {capture_fields} "" "{path}"')
  chunk=[json.loads(x) for x in path.read_text().splitlines()];meta=chunk[0]
  piece=chunk[1:];changes=[x['field'] for prev,x in zip(piece,piece[1:]) if prev['planes']!=x['planes']]
  intervals.extend(b-a for a,b in zip(changes,changes[1:]))
  for x in piece:x['field']=len(rows);rows.append(x)
  if len(intervals)>=300:break
 assert len(intervals)>=300,len(intervals)
 assert all(all(x['planes']) for x in rows)
 (out/'window.jsonl').write_text('\n'.join(json.dumps(x) for x in [meta]+rows)+'\n')
 intervals=intervals[:300];report['fps_end']=context();fields=sum(intervals)
 import statistics,math
 report['fps']=300/(fields*71051/3546895);report['fps_fields']=fields;report['interval_fields']=intervals;report['mean_ms']=statistics.mean(intervals)*71051/3546895*1000;report['p95_ms']=sorted(intervals)[math.ceil(len(intervals)*.95)-1]*71051/3546895*1000
 report['measurement']='300 complete displayed-buffer intervals after 100 presentation calls, excluding each census window boundary; warp off. Concatenated window.jsonl is a storage view, not a continuous timing timeline.';report['census_metadata']=meta
 if 'HeavyFrames' in sy:
  report['heavy_frames']=val(f'*(unsigned int*){probe+sy['HeavyFrames']}');report['heavy_incomplete']=val(f'*(unsigned int*){probe+sy['HeavyIncomplete']}');assert report['heavy_incomplete']==0
 report['error']=val(f'*(unsigned int*){probe+sy["error"]}');report['status']='passed' if report['error']==0 and report['fps']>=(3.494 if kind=='000' else 5.54) else 'failed'
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True);assert report['status']=='passed'

finally:
 import shutil
 for artifact in ('launch.json','fsuae.log'):
  if (r/'amiga/.run'/artifact).exists():shutil.copy(r/'amiga/.run'/artifact,out/artifact)
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
