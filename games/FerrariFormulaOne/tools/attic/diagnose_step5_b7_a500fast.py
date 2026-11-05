from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a1200-fast';name=os.environ.get('B7_LABEL','b7-v2-smoke')+'-'+profile;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=Path(os.environ.get('SLAVE',str(r/'tmp/build/step5-b7-v2/lean/fine.slave')));profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2='+os.environ.get('B7_CUSTOM2','1'),DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),profile_window=False);log=[]
try:
 g=s.boot()
 def cmd(c):
  try:v=g.cmd(c,timeout=45)
  except TimeoutError:
   os.kill(g.p.pid,signal.SIGINT);stopped=g.read_until(g.sent,20)
   (out/'timeout-registers.txt').write_text(stopped+'\n'+g.cmd('info registers'))
   g.cmd(f'monitor profile 1 \"\" \"{out}/timeout-screen.bin\"',timeout=60)
   from amigaxdev import barto
   (out/'timeout-screen.png').write_bytes(barto.load(out/'timeout-screen.bin').fields[-1].shot)
   dump('timeout-memory')
   raise
  log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
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
 for attempt in range(200):
  v=cmd('continue');assert 'Breakpoint' in v,v
  if val('*(unsigned int*)$a3')==0x22f30:
   race=val('$d0+*(unsigned int*)($a3+28)');break
 else:raise AssertionError('No race overlay entered')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 cmd('delete');cmd(f'break *{race+0xb9e}');v=cmd('continue');assert 'Breakpoint' in v,v
 if os.environ.get('B7_TRACE'):
  cmd('delete');cmd('monitor warp 0')
  cmd('dump binary memory tmp/step5/b7-v2-smoke/before-draw.bin 0 0x600000')
  cmd(f'monitor profile 16 "" "{out}/draw.bin"')
  cmd('dump binary memory tmp/step5/b7-v2-smoke/after-draw.bin 0 0x600000')
  print(cmd('info registers'),flush=True)
  raise SystemExit(0)
 cmd(f'ignore $bpnum 129');assert 'Breakpoint' in cmd('continue')
 memory=dump('loop130')
 import re
 host_listing=(r/'tmp/build/step5-b7-loader-v2/build.list').read_text(errors='replace');fine_listing=(b.parent/'fine.list').read_text()
 def sym(text,n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',text,re.M)[1],16)
 probe=marker-sym(host_listing,'FF1PublicMarker')+len((r/'tmp/build/step5-b7-loader-v2/FerrariFormulaOne.slave').read_bytes()[32:-4])
 report['probe']=hex(probe)
 report['stack_pointer']=val('$sp')
 report['stack_owner']=val(f'*(unsigned int*){marker-sym(host_listing,"FF1PublicMarker")+sym(host_listing,"FF1PublicStackOwner")}')
 report['state']={n:val(f'*(unsigned int*){probe+sym(fine_listing,n)}') for n in ('selection_path','selection_interval','public_table','public_bound','public_binding_error','installed','ticks','error','public_fallbacks','public_unload_installed')}
 from step5_b7_addresses import Addresses
 rows=Addresses(memory,table).rows
 report['placements']=[dict(x,kind='Fast' if 0x200000<=x['actual']<0xa00000 else 'Slow' if 0xc00000<=x['actual']<0xd80000 else 'Chip') for x in rows]
 assert all(x['kind']=='Fast' for x in report['placements'] if x['hunk']<=205 and x['hunk']!=46) if profile.endswith('-fast') else True
 assert next(x for x in report['placements'] if x['hunk']==46)['kind']=='Chip'
 fine=profile=='a1200-fast' and os.environ.get('B7_EXPECT_COARSE')!='1'
 assert report['state']['selection_path']==(2 if fine else 1),report
 assert report['state']['installed']==int(fine) and report['state']['error']==0,report
 assert val(f'*(unsigned int*){marker-sym(host_listing,"FF1PublicMarker")+sym(host_listing,"FF1PublicPatchError")}')==0
 if os.environ.get('B7_NO_STACK')!='1':assert report['stack_owner']<=report['stack_pointer']<report['stack_owner']+32768,report
 if os.environ.get('B7_EXPECT_COARSE')=='1':assert report['state']['public_fallbacks']==1,report
 report['status']='passed';report['profile']=profile
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(profile,report['status'],report['state'],flush=True)
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
