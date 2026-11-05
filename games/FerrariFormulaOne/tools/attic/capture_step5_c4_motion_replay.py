from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a1200-fast';variant=os.environ.get('C1_VARIANT','candidate');name='c4-boundary-p5-v3-ab-'+profile+'-'+variant+'-replay';out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=r/'tmp/build/step5-c4-boundary-p5-v3-ab'/('000' if profile.startswith('a500') else '020')/(variant+'.slave');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else os.environ['KICKSTART'])
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

 from step5_b7_addresses import Addresses
 cmd('delete');cmd(f'break *{probe+sym(fine_listing,"C1Checkpoint")}');assert 'Breakpoint' in cmd('continue')
 cmd('monitor warp 0')
 memory=dump('start-raw');addresses=Addresses(memory,table);(out/'addresses.json').write_text(json.dumps(addresses.rows,indent=2))
 (out/'start.bin').write_bytes(addresses.canonical_memory(memory))
 def read(at,n):
  path=out/'current.bin';cmd(f'dump binary memory {path.relative_to(r)} {at} {at+n}');data=path.read_bytes();assert len(data)==n;return data
 def scalar(name):return val(f'*(unsigned int*){probe+sym(fine_listing,name)}')
 native_index=addresses.map(0x32fbc);native_velocity=addresses.map(0x32f94)
 scratch=probe+sym(fine_listing,'velocity_scratch');speed=probe+sym(fine_listing,'speed_work')
 velocities=probe+sym(fine_listing,'velocity_shadow');positions=probe+sym(fine_listing,'position_shadow')
 labels=['FF1VelocityProject000','C4SaveMask013','fine_advance','C4SaveMask041','C1Checkpoint','velocity_stop','C1Fault']
 sites={probe+sym(fine_listing,n):n for n in labels}
 cmd('delete')
 for pc in sites:cmd(f'break *{pc}')
 pending_v={};pending_p={};vr=[];pr=[];updates=0
 start_completed=scalar('C1Completed')
 while updates<100:
  assert 'Breakpoint' in cmd('continue')
  pc=val('$pc');event=sites[pc]
  assert event not in ('velocity_stop','C1Fault'),(event,scalar('error'))
  if event=='C1Checkpoint':
   assert not pending_v and not pending_p,(pending_v,pending_p)
   updates+=1
   if updates%20==0:print('Replay updates',updates,flush=True)
   continue
  car=val(f'*(unsigned short*){native_index}');assert 0<=car<8
  if event=='FF1VelocityProject000':
   assert car not in pending_v
   pending_v[car]={'update':updates,'car':car,'speed_input':val('$d0'),'shadow_before':read(velocities+car*12,12).hex(),'angle':struct.unpack('>H',read(scratch+2,2))[0]}
  elif event=='C4SaveMask013':
   row=pending_v.pop(car);row.update(scratch=read(scratch,80).hex(),shadow_after=read(velocities+car*12,12).hex(),speed_after=read(speed,6).hex(),native_velocity=read(native_velocity,4).hex());vr.append(row)
  elif event=='fine_advance':
   assert car not in pending_p
   pending_p[car]={'update':updates,'car':car,'shadow_before':read(positions+car*12,12).hex(),'velocity':read(velocities+car*12,12).hex(),'native_before':read(native_index,16).hex()}
  elif event=='C4SaveMask041':
   row=pending_p.pop(car);row.update(shadow_after=read(positions+car*12,12).hex(),native_after=read(native_index,16).hex());pr.append(row)
 (out/'velocity.json').write_text(json.dumps(vr)+'\n');(out/'position.json').write_text(json.dumps(pr)+'\n')
 report.update(updates=updates,velocity_records=len(vr),position_records=len(pr),start_completed=start_completed,end_completed=scalar('C1Completed'),error=scalar('error'),warp_end=cmd('monitor warp-status'),status='complete')
 assert report['error']==0 and report['end_completed']-start_completed==100
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
