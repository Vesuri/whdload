# FR3 probe (FASTRAM_PLAN.md FR3): boot a FF1_FAST_RENDER build, stop at the
# first FF1FastRenderPublish (mirrors seeded, nothing drawn since), compare
# every mirror with Chip, then run N more draws and read FF1FastRenderStats.
#   fr3_probe.py PROFILE [DRAWS]      env FR3_BUILD, FR3_TAG
# Output tmp/step5/fr3-probe-PROFILE[TAG]/result.json
from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1];draws=int(sys.argv[2]) if len(sys.argv)>2 else 50
out=r/'tmp/step5'/('fr3-probe-'+profile+os.environ.get('FR3_TAG',''));out.mkdir(parents=True,exist_ok=True)
b=Path(os.environ.get('FR3_BUILD',str(r/'tmp/build/fr3-candidate')))/'FerrariFormulaOne.slave'
profiles=json.loads((r/'tmp/manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile])
os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1'),DETERMINISTIC='1',
 FSUAE=os.environ.get('RELEASE_FSUAE',str(r/'tmp/step5-frame-observer-build/fs-uae')),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'])
s=Server('ff1measure',root=str(r),run_script='tools/run.sh',run_dir='tmp/run/default/.run',profile_window=False);log=[];report={}
STATS=['tag','installs','active','reject_cpu','reject_layout','alloc_fail','seeds','releases','publishes','free_before','largest_before','min_free_after','block_bytes']
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
  emulator=os.environ['FSUAE'],cpu=os.environ['CPU'])
 def stats():
  raw=dump('stats',probe+sy['FF1FastRenderStats'],probe+sy['FF1FastRenderStats']+4*len(STATS))
  return dict(zip(STATS,struct.unpack('>%dI'%len(STATS),raw)))
 cmd('delete')
 for n in ['velocity_fault','schedule_bad']:
  if n in sy:cmd(f'break *{probe+sy[n]}')
 cmd(f'break *{host+hs["FF1WrongVersion"]}')
 cmd(f'break *{probe+sy["FF1FastRenderPublish"]}');cmd('set $frbp=$bpnum')
 if os.environ.get('FR3_FREEWATCH'):
  # Who frees the race-start transient during the first field wait?
  cmd(f'break *{probe+sy["FF1FastRenderAllocate"]}');v=cmd('continue',timeout=1800)
  eb=val('*(unsigned int*)4');fm=val(f'*(unsigned int*){eb-210+2}')
  cmd('delete');cmd(f'break *{fm} if $a1>=0x92e000 && $a1<0x931000');n=0
  while n<6:
   v=cmd('continue',timeout=600);ra=val('*(unsigned int*)$sp')
   print('FreeMem',hex(val('$a1')),val('$d0'),'ra',hex(ra),'ra2',hex(val('*(unsigned int*)($sp+4)')),'task',hex(val(f'*(unsigned int*){eb+276}')),flush=True);n+=1
  raise SystemExit(0)
 t0=time.time();v=cmd('continue',timeout=1800)
 assert val('$pc')==probe+sy['FF1FastRenderPublish'],(hex(val('$pc')),v)
 report['first_publish_seconds']=round(time.time()-t0,1)
 report['stats_first']=stats()
 active=val(f'*(unsigned short*){probe+sy["FF1FastRenderActive"]}')
 report['active']=active
 mirrors=[]
 if active:
  mem=full('seeded')
  tab=dump('mirrors',probe+sy['FF1FastRenderMirrors'],probe+sy['FF1FastRenderMirrors']+16*8+4)
  delta=dump('delta',probe+sy['FF1FastRenderDelta'],probe+sy['FF1FastRenderDelta']+16*4)
  block=val(f'*(unsigned int*){probe+sy["FF1FastRenderBlock"]}');bbytes=val(f'*(unsigned int*){probe+sy["FF1FastRenderBlockBytes"]}')
  report.update(block=hex(block),block_bytes=bbytes)
  for i in range(16):
   lo,hi=struct.unpack_from('>II',tab,8*i);d=struct.unpack_from('>i',delta,4*i)[0];f=lo+d
   assert block<=f and f+hi-lo<=block+bbytes and f%16==lo%16,(i,hex(lo),hex(f))
   diff=sum(1 for j in range(hi-lo) if mem[lo+j]!=mem[f+j])
   mirrors.append(dict(chip=[hex(lo),hex(hi)],fast=hex(f),differing_bytes=diff))
 report['mirrors']=mirrors
 cmd('delete $frbp')
 cmd(f'break *{probe+sy["B8Draw"]}');cmd('set $b8=$bpnum')
 cmd(f'ignore $b8 {draws-1}');v=cmd('continue',timeout=1800)
 assert val('$pc')==probe+sy['B8Draw'],(hex(val('$pc')),v)
 report['stats_after']=stats();report['draws']=draws
 report['status']='passed' if active and all(m['differing_bytes']==0 for m in mirrors) else ('inactive' if not active else 'failed')
 (out/'result.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1),flush=True)
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if not (out/'result.json').exists():(out/'result.json').write_text(json.dumps(dict(report,status='error'),indent=1)+'\n')
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
