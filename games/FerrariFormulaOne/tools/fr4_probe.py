# FR4 probe (FASTRAM_PLAN.md FR4): boot a FF1_FAST_RENDER build, run DRAWS
# draws past the first publication and read FF1FastRenderStats (FR3S) and
# FF1FastRenderSiteStats (FR4S: software/hardware blits per site, faults).
# A break on FF1FastRenderFault or FF1ProductionFault reports the fault.
#   fr4_probe.py PROFILE [DRAWS]      env FR4_BUILD (or FF1_BUILD), FR4_TAG
# Exits 1 unless the probe passed (ff1check.py fastrender).
# Output tmp/step5/fr4-probe-PROFILE[TAG]/result.json
from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1];draws=int(sys.argv[2]) if len(sys.argv)>2 else 50
out=r/'tmp/step5'/('fr4-probe-'+profile+os.environ.get('FR4_TAG',''));out.mkdir(parents=True,exist_ok=True)
b=Path(os.environ.get('FR4_BUILD') or os.environ.get('FF1_BUILD') or str(r/'tmp/build/fr4-candidate'))/'FerrariFormulaOne.slave'
profiles=json.loads((r/'tmp/manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile])
os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1'),DETERMINISTIC='1',
 FSUAE=os.environ.get('RELEASE_FSUAE',str(r/'tmp/step5-frame-observer-build/fs-uae')),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'])
s=Server('ff1measure',root=str(r),run_script='tools/run.sh',run_dir='tmp/run/default/.run',profile_window=False);log=[];report={}
STATS=['tag','installs','active','reject_cpu','reject_layout','alloc_fail','seeds','releases','publishes','free_before','largest_before','min_free_after','block_bytes']
SITES=['24c18','24db8','6ad8a','6adde','fill','32dfa','32e6c','32f02','6c55c','6bbec','pixel']
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
  a=dict(zip(STATS,struct.unpack('>%dI'%len(STATS),raw)))
  raw=dump('stats4',probe+sy['FF1FastRenderSiteStats'],probe+sy['FF1FastRenderSiteStats']+152)
  v=struct.unpack('>38I',raw)
  a['fr4']=dict(tag=v[0],soft=dict(zip(SITES,v[1:12])),hard=dict(zip(SITES,v[17:28])),redirects=v[33],faults=v[34],fault_reason=v[35],fault_site=v[36],site_installs=v[37])
  if 'FF1FastRenderStageStats' in sy:
   raw=dump('stats5',probe+sy['FF1FastRenderStageStats'],probe+sy['FF1FastRenderStageStats']+32)
   a['fr5']=dict(zip(['tag','prefixes','published','refreshed','filled','cuts','blocks_refreshed','blocks_published'],struct.unpack('>8I',raw)))
  if 'FF1FastRenderCopyStats' in sy:
   raw=dump('stats7',probe+sy['FF1FastRenderCopyStats'],probe+sy['FF1FastRenderCopyStats']+20)
   a['fr7']=dict(zip(['tag','rows','written','flushes','view_seeds'],struct.unpack('>5I',raw)))
  if 'FF1FastRenderBlocks' in sy:
   raw=dump('blocks',probe+sy['FF1FastRenderBlocks'],probe+sy['FF1FastRenderBlocks']+1000)
   segs=[(0xcd30,0xd3e0),(0xd3e0,0x18f48),(0x18f48+30960,0x528d8)];out=[];o=0
   for lo,hi in segs:
    n=(hi-lo+255)>>8
    for i in range(n):
     if raw[o+i]==2:out.append(hex(lo+i*256))
    o+=n
   a['dirty_blocks']=out
  if 'FF1FastRenderChipReads' in sy:
   at=probe+sy['FF1FastRenderChipReads'];raw=dump('chipreads',at,at+8+8*512+4)
   n,e=struct.unpack_from('>2I',raw)
   a['chipreads']=dict(spans=n,entries=e,unlogged=struct.unpack_from('>I',raw,8+8*512)[0],
    ranges=sorted(struct.unpack_from('>2I',raw,8+8*i) for i in range(min(e,512))))
  return a
 cmd('delete')
 for n in ['velocity_fault','schedule_bad']:
  if n in sy:cmd(f'break *{probe+sy[n]}')
 cmd(f'break *{host+hs["FF1WrongVersion"]}')
 cmd(f'break *{probe+sy["FF1FastRenderFault"]}');cmd('set $fault=$bpnum')
 cmd(f'break *{probe+sy["FF1ProductionFault"]}');cmd('set $pfault=$bpnum')
 cmd(f'break *{probe+sy["FF1FastRenderPublish"]}');cmd('set $frbp=$bpnum')
 def stopped(v):
  pc=val('$pc')
  if pc in (probe+sy['FF1FastRenderFault'],probe+sy['FF1ProductionFault']):
   report['fault']=dict(pc=hex(pc),regs=cmd('info registers'),site=val(f'*(unsigned short*){probe+sy["FF1FastRenderSite"]}'),
    image=dump('image',probe+sy['FF1FastRenderImage'],probe+sy['FF1FastRenderImage']+0x3c).hex(),stack=dump('stack',val('$sp'),val('$sp')+96).hex(),a6frame=dump('a6frame',val('$a6')-16,val('$a6')+32).hex())
   try:
    st=val('*(unsigned int*)($a6+8)');report['fault']['a6arg']=hex(st);report['fault']['a6struct']=dump('a6struct',st,st+64).hex()
   except Exception as e:report['fault']['a6arg_error']=str(e)
   try:
    ret=val('*(unsigned int*)($sp+60)');report['fault']['thunk_return']=hex(ret)
    nat=val('*(unsigned int*)($sp+72)');report['fault']['native_return']=hex(nat)
    report['fault']['native_code']=dump('native',nat-0xb0,nat+0x20).hex()
    report['fault']['regs_base']=hex(val(f'*(unsigned int*){probe+sy["FF1FastRenderRegs"]}'))
    report['fault']['redirect']=val(f'*(unsigned short*){probe+sy["FF1FastRenderRedirect"]}')
   except Exception as e:report['fault']['extra_error']=str(e)
   report['stats_fault']=stats();report['status']='fault'
   raise SystemExit(1)
  return pc
 t0=time.time();v=cmd('continue',timeout=1800)
 assert stopped(v)==probe+sy['FF1FastRenderPublish'],(hex(val('$pc')),v)
 report['first_publish_seconds']=round(time.time()-t0,1)
 report['stats_first']=stats()
 report['active']=val(f'*(unsigned short*){probe+sy["FF1FastRenderActive"]}')
 cmd('delete $frbp')
 cmd(f'break *{probe+sy["B8Draw"]}');cmd('set $b8=$bpnum')
 cmd('continue',timeout=600);assert stopped(None)==probe+sy['B8Draw']
 report['stats_draw1']=stats()
 cmd(f'ignore $b8 {draws-1}');v=cmd('continue',timeout=1800)
 assert stopped(v)==probe+sy['B8Draw'],(hex(val('$pc')),v)
 report['stats_after']=stats();report['draws']=draws
 if 'FF1FastRenderView' in sy:
  # FR7: between draws both Chip banks show their shadows' displayed region
  # (bytes 4..43 of rows 0..199 of each plane), and in copy mode 2 the view
  # mirror holds the same bytes.
  mem=full('views');u=lambda a:struct.unpack_from('>I',mem,a)[0]
  mode=struct.unpack_from('>H',mem,probe+sy['FF1FastRenderCopy'])[0];view=u(probe+sy['FF1FastRenderView'])
  bad={'shadow':0,'view':0}
  for bank,base in enumerate((0x18f48,0x528d8)):
   sh=base+u(probe+sy['FF1FastRenderDelta']+4*bank)
   for pl in range(3):
    for row in range(200):
     o=pl*10320+row*48+4;c=mem[base+o:base+o+40]
     bad['shadow']+=c!=mem[sh+o:sh+o+40]
     v=view+((bank*3+pl)*200+row)*40
     bad['view']+=mode==2 and c!=mem[v:v+40]
  report['fr7_check']=dict(copy_mode=mode,rows_differing=bad)
 a,b0=report['stats_after']['fr4'],report['stats_draw1']['fr4']
 report['per_draw']={k:{s:round((a[k][s]-b0[k][s])/draws,2) for s in SITES} for k in ('soft','hard')}
 report['status']='passed' if report['active'] and a['faults']==0 and not any(report.get('fr7_check',{}).get('rows_differing',{}).values()) else 'failed'
 (out/'result.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in('stats_first','stats_draw1')},indent=1),flush=True)
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if not (out/'result.json').exists() or report.get('status')=='fault':(out/'result.json').write_text(json.dumps(dict(report,status=report.get('status','error')),indent=1)+'\n')
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
sys.exit(0 if report.get('status')=='passed' else 1)
