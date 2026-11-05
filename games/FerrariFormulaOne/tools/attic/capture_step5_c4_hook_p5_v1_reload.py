from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a1200-fast';variant=os.environ.get('C1_VARIANT','candidate');name='c4-hook-p5-v1-ab-'+profile+'-reload';out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/step5-c4-hook-p5-v1-ab-reload'/('000' if profile.startswith('a500') else '020')/(variant+'.slave');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
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

 def scalar(n):return val(f'*(unsigned int*){probe+sym(fine_listing,n)}')
 def activation(label):
  cmd('delete');cmd(f'break *{probe+sym(fine_listing,"FF1InstallCoarse200")}');assert 'Breakpoint' in cmd('continue')
  ret=val('*(unsigned int*)$sp')
  report[label+'_before_initialized']=val(f'*(unsigned short*){probe+sym(fine_listing,"velocity_initialized")}')
  cmd('delete');cmd(f'break *{ret}');assert 'Breakpoint' in cmd('continue')
  memory=dump(label)
  names={'velocity_initialized':2,'velocity_shadow':96,'speed_shadow':48,'position_shadow':96,'heading_shadow':96,'steering_shadow':144,'wear_remainders':24,'fuel_remainders':16}
  return {n:memory[probe+sym(fine_listing,n):probe+sym(fine_listing,n)+size].hex() for n,size in names.items()}
 report['first']=activation('first')
 cmd('delete');cmd(f'break *{probe+sym(fine_listing,"C1Unload")}');assert 'Breakpoint' in cmd('continue')
 report['intenar_before_unload']=val('*(unsigned short*)0xdff01c');assert not report['intenar_before_unload']&64
 report['before_unload']={n:scalar(n) for n in ('C1Completed','public_bound','public_reload_count','error')}
 cmd('delete');cmd(f'break *{root+0x2e6} if *(unsigned int*)$a3 == 0x22f30');assert 'Breakpoint' in cmd('continue')
 race2=val('$d0+*(unsigned int*)($a3+28)');report['race2']=hex(race2)
 assert race2!=race
 report['after_restore']={n:scalar(n) for n in ('C1Heads','C1Completed','public_bound','error')}
 assert report['after_restore']==dict(C1Heads=0,C1Completed=0,public_bound=0,error=0)
 report['intenar_after_restore']=val('*(unsigned short*)0xdff01c');assert report['intenar_after_restore']&64
 assert val(f'*(unsigned short*){probe+sym(fine_listing,"C4BlitOwned")}')==0
 report['second']=activation('second')
 report['different_activation_state']=[n for n in report['first'] if report['first'][n]!=report['second'][n]]
 assert report['second']['velocity_initialized']=='0000'
 assert report['second']['position_shadow']=='00'*96
 from step5_b7_addresses import Addresses
 addresses=Addresses(dump('second-native'),table)
 def native_word(at):return val(f'*(unsigned short*){addresses.map(at)}')
 report['seeded_cars']=[]
 for i in range(8):
  cmd('delete');cmd(f'break *{probe+sym(fine_listing,"velocity_load")}');assert 'Breakpoint' in cmd('continue')
  car=native_word(0x32fbc);vx=native_word(0x32f94);vz=native_word(0x32f96)
  assert car not in report['seeded_cars']
  ret=val('*(unsigned int*)$sp')
  cmd('delete');cmd(f'break *{ret}');assert 'Breakpoint' in cmd('continue')
  at=probe+sym(fine_listing,'velocity_shadow')+12*car
  actual=[val(f'*(unsigned int*){at+j}') for j in (0,4,8)]
  assert actual==[vx<<16,vz<<16,0],(car,actual,vx,vz)
  report['seeded_cars'].append(car)
 cmd('delete');cmd(f'break *{probe+sym(fine_listing,"C1Checkpoint")} if *(unsigned int*){probe+sym(fine_listing,"C1Completed")} == 20');assert 'Breakpoint' in cmd('continue')
 report['reentered']={n:scalar(n) for n in ('C1Completed','error','public_reload_hold')}
 assert report['reentered']==dict(C1Completed=20,error=0,public_reload_hold=0)
 report['intenar_after_reactivation']=val('*(unsigned short*)0xdff01c');assert not report['intenar_after_reactivation']&64
 report['owned_after_reactivation']=val(f'*(unsigned short*){probe+sym(fine_listing,"C4BlitOwned")}');assert report['owned_after_reactivation']==64
 report['status']='passed' 
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('first','second')},flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
