from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a1200-fast';variant=os.environ.get('C1_VARIANT','candidate');name='c4-blit-d1-v2-ab-'+profile+'-exit';out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/step5-c4-blit-d1-v2-ab-exit'/('000' if profile.startswith('a500') else '020')/(variant+'.slave');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
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
 for attempt in range(200):
  v=cmd('continue');assert 'Breakpoint' in v,v
  if val('*(unsigned int*)$a3')==0x22f30:
   race=val('$d0+*(unsigned int*)($a3+28)');break
 else:raise AssertionError('No race overlay entered')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')

 import re
 host_listing=(r/'tmp/build/step5-b7-loader-v3/build.list').read_text(errors='replace');fine_listing=(b.parent/'fine.list').read_text()
 def sym(text,n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',text,re.M)[1],16)
 probe=marker-sym(host_listing,'FF1PublicMarker')+len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes()[32:-4])
 report['probe']=hex(probe)

 cmd('delete');cmd(f'break *{probe+sym(fine_listing,"C1Exit")}');assert 'Breakpoint' in cmd('continue')
 report['intenar_active']=val('*(unsigned short*)0xdff01c');assert not report['intenar_active']&64
 report['owned_active']=val(f'*(unsigned short*){probe+sym(fine_listing,"C4BlitOwned")}');assert report['owned_active']==64
 report['completed_before']=val(f'*(unsigned int*){probe+sym(fine_listing,"C1Completed")}');assert report['completed_before']==10
 memory=dump('active-raw')
 from step5_b7_addresses import Addresses
 at=Addresses(memory,table).map(0x29500)
 assert memory[at:at+2]==bytes.fromhex('4ef9')
 assert struct.unpack_from('>I',memory,at+2)[0]==probe+sym(fine_listing,'FF1MultiplyNative200')
 report['multiply_hook_confirmed']=True
 project_at=Addresses(memory,table).map(0x6dc52)
 assert memory[project_at:project_at+4]==bytes.fromhex('60000042')
 report['projection_bypass_confirmed']=True
 cmd('delete');cmd(f'break *{race+0x14e0}');assert 'Breakpoint' in cmd('continue')
 report['after']={n:val(f'*(unsigned int*){probe+sym(fine_listing,n)}') for n in ('C1Heads','C1Completed','public_bound','error')}
 assert all(v==0 for v in report['after'].values())
 assert val(f'*(unsigned int*){probe+sym(fine_listing,"C1Ledger")}')==val(f'*(unsigned int*){probe+sym(fine_listing,"C1Ledger")+8}')==0
 assert val(f'*(unsigned short*){race+0x70c}')==0x3039
 assert val(f'*(unsigned short*){race+0x14e0}')==0x4eb9
 memory=dump('restored-raw')
 from step5_b7_addresses import Addresses
 canonical=Addresses(memory,table).canonical_memory(memory)
 native=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
 for at,n in ((0x6dc52,0x44),(0x29500,66),(0x293d0,66),(0x6977a,0x112),(0x24fe0,64)):
  assert canonical[at:at+n]==native[at:at+n],hex(at)
 report['restored_helpers']=['projection','multiply','division','lookahead','sin/cos']
 report['intenar_restored']=val('*(unsigned short*)0xdff01c');assert report['intenar_restored']==report['intenar_active']|64
 assert val(f'*(unsigned short*){probe+sym(fine_listing,"C4BlitOwned")}')==0
 report['status']='passed';(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
