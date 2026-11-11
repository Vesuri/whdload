from pathlib import Path
import os,sys,time,signal,json,struct,hashlib,mmap
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
from amigaxdev.input import Input
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='controls';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=Path(os.environ.get('DRIVE_SLAVE',str(r/'tmp/build/production/FerrariFormulaOne.slave')));profiles=json.loads((r/'tmp/manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='none',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1 ConfigDelay=0'),DETERMINISTIC='1',FSUAE=os.environ.get('RELEASE_FSUAE',os.environ['FSUAE_ARM']),KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),run_script=os.environ.get('RELEASE_RUN_SCRIPT','tools/run.sh'),run_dir='tmp/run/default/.run',profile_window=False);log=[];controls=None
try:
 g=s.boot()
 controls=Input(g)
 def cmd(c):
  if c.startswith('monitor input '):
   _,_,event,state=c.split()
   if event=='KEY_SPACE':controls.key(0x40,int(state))
   else:controls.button(event,int(state))
   v=''
  elif c.startswith('monitor mouse '):
   dx,dy=map(int,c.split()[2:]);controls.mouse(dx,dy);v=''
  else:v=g.cmd(c,timeout=180)
  log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):
  chip=int(os.environ['CHIP_KB'])*1024
  cmd(f'dump binary memory {out.relative_to(r)}/{label}.bin 0 {chip}')
  mem=(out/(label+'.bin')).read_bytes()
  for bank,base,key in [('fast',0x200000,'FAST_KB'),('slow',0xc00000,'SLOW_KB'),('z3',0x40000000,'DRIVE_Z3_KB')]:
   size=int(os.environ.get(key,'0'))*1024
   if size:
    cmd(f'dump binary memory {out.relative_to(r)}/{label}-{bank}.bin {base} {base+size}')
    if not (out/(label+'-'+bank+'.bin')).exists():
     if bank=='z3':continue
     raise RuntimeError('Memory bank unavailable: '+bank)
    data=(out/(label+'-'+bank+'.bin')).read_bytes()
    if bank=='z3':
     mapped=mmap.mmap(-1,base+size);mapped[:len(mem)]=mem;mapped[base:base+size]=data;mem=mapped
    else:mem+=bytes(base-len(mem))+data
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
 if len(hits)!=1:
  cmd('delete');s.handle(g,'shot '+str(out/'boot-failure.png'))
 assert len(hits)==1,hits
 marker,root=hits[0];table=u(root+16)*4;race=u(table+160*4)*4+4
 report=dict(root=hex(root),table=hex(table),race=hex(race),marker=hex(marker),pc=val('$pc'),slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
 if race <= 4:
  cmd('delete');cmd(f'break *{root+0x2e6}')
  cmd('condition $bpnum *(unsigned int*)$a3 == 0x22f30')
  assert 'Breakpoint' in cmd('continue')
  race=val('$d0+*(unsigned int*)($a3+28)')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')

 import re
 build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine';module=build['payloads'][kind];sy=module['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+module['offset']
 fine=kind=='fine'
 aliases={'C1Checkpoint':'FF1PresentationAfterTick','C1Context':'schedule_context','C1Pause':'FF1FinePause','C1Resume':'FF1FineResume','C1Vbl':'schedule_vbl','C1Ledger':'public_patch_context','C1Completed':'schedule_completed'} if fine else {}
 def sym(text,n):return sy[aliases.get(n,n)]
 fine_listing='';host_listing=''
 report['probe']=hex(probe);report['kind']=kind
 cmd('delete')
 for failure in (('velocity_stop','schedule_bad') if fine else ('C1Fault',)):
  cmd(f'break *{probe+sym(fine_listing,failure)}')
 cmd(f'break *{probe+sym(fine_listing,"C1Checkpoint")}');assert 'Breakpoint' in cmd('continue'),log[-1]
 if val('$pc')!=probe+sym(fine_listing,'C1Checkpoint'):
  report['error']=val(f'*(unsigned int*){probe+sym(fine_listing,"error")}')
  report['registers']=cmd('info registers')
  dump('fault')
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  raise AssertionError(report)
 from step5_b7_addresses import Addresses
 memory=dump('input-start');addresses=Addresses(memory,table)
 def native(addr):return addresses.map(addr)
 def until(address,condition=None):
  cmd('delete');cmd(f'break *{address}')
  if condition:cmd('condition $bpnum '+condition)
  assert 'Breakpoint' in cmd('continue'),log[-1]
  assert val('$pc')==address
 def key(event,code):
  target=native(0x23708)
  cmd('delete');cmd(f'break *{target}')
  irq=host+hs['keyboard_start']
  cmd(f'break *{irq}')
  cmd(f'break *{native(0x2482a)}')
  report.setdefault('input_commands',[]).append(cmd('monitor input '+event+' 1'))
  found=False
  for attempt in range(64):
   assert 'Breakpoint' in cmd('continue'),log[-1]
   pc=val('$pc')
   if pc in (irq,native(0x2482a)):
    report.setdefault('input_path',[]).append(dict(pc=hex(pc),d0=val('$d0')))
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
   if pc==target:
    got=val('$d0')&255
    report.setdefault('key_reads',[]).append(dict(event=event,expected=code,actual=got,pc=hex(pc),raw_caller=hex(val('*(unsigned int*)($a6+4)')),translated_caller=hex(val('*(unsigned int*)(*(unsigned int*)$a6+4)'))))
    if got==code:found=True;break
   if attempt==8 and event=='KEY_SPACE':
    cmd('monitor input '+event+' 0')
   if attempt==12 and event=='KEY_SPACE':
    cmd('monitor input '+event+' 1')
  cmd('monitor input '+event+' 0')
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  if not found:dump('input-delivery-failure')
  assert found,report
 def save():
  report['extra_args']=os.environ.get('EXTRA_ARGS','');report['emulator_sha256']=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest();report['launch']=json.loads((r/'tmp/run/default/.run/launch.json').read_text());report['runtime_sha256']=hashlib.sha256((r/'tmp/run/default/.run/dh1/WHDLoad').read_bytes()).hexdigest()
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def snapshot(label):
  m=dump(label);ctx=list(struct.unpack_from('>14I',m,probe+sym(fine_listing,'C1Context')))
  v={'context':ctx,'completed':struct.unpack_from('>I',m,probe+sym(fine_listing,'C1Context')+24)[0],'owned':(struct.unpack_from('>H',m,probe+sy['C4BlitOwned'])[0] if kind=='000' else 0),'calendar':m[native(0x226c0):native(0x226c0)+10].hex(),'session':m[native(0x226ca):native(0x226ca)+10].hex()}
  report[label]=v;save();return m,v
 def advance_fields(n,active=True):
  cmd('delete');cmd(f'break *{probe+sym(fine_listing,"C1Vbl") if active else native(0x2482a)}');cmd(f'ignore $bpnum {n-1}');assert 'Breakpoint' in cmd('continue')
 # WARP=1 is set before launch; no private monitor command.
 key('KEY_SPACE',0x40)
 until(probe+sym(fine_listing,'C1Checkpoint'))
 memory,take=snapshot('takeover')
 # WARP=1 is set before launch; no private monitor command.
 def row(label):
  until(0x65174 if kind=='legacy' else probe+sym(fine_listing,'C1Checkpoint'))
  d={'label':label}
  for n,addr in {'speed':0x2275a,'gear':0x66c3c,'rpm':0x6f270,'buttons':0x66f92,'countdown':0x66f94,'latch':0x32f92,'mode':0x1c1c2,'difficulty':0x1c1c4,'steering':0x1c6a2,'mouse_x':0x24aa8,'heading':0x6a66a,'segment':0x6a60a,'longitudinal':0x6a62a,'lateral':0x6a61a,'status':0x2268e,'demo':0x1bee8}.items():d[n]=val(f'*(unsigned short*){native(addr)}')
  d['automatic_gear']=val(f'*(unsigned char*){native(0x6f0e8)}')
  if os.environ.get('DRIVE_CARS')=='1':d['cars']=[(val(f'*(unsigned short*){native(0x6a60a+2*i)}'),val(f'*(unsigned short*){native(0x6a62a+2*i)}'),val(f'*(short*){native(0x6a61a+2*i)}')) for i in range(8)]
  if kind!='legacy':d['error']=val(f'*(unsigned int*){probe+sy['error']}');assert d['error']==0
  report.setdefault('drive',[]).append(d);save();print(d,flush=True);return d
 row('takeover')
 clutch=os.environ.get('DRIVE_CLUTCH')=='1'
 if clutch:cmd('monitor input JOY1_FIRE_BUTTON 1');cmd('monitor input JOY1_2ND_BUTTON 1')
 advance_fields(150,False);start=row('ready')
 assert start['countdown']==0,start
 # A start-line contact can move the car before the test drives it (the A500's demo grid
 # slot meets the original's collision response): brake it to rest, then drive as usual.
 if start['speed'] and not clutch:
  cmd('monitor input JOY1_FIRE_BUTTON 1')
  for i in range(10):
   advance_fields(30,False);start=row('settling-'+str(i))
   if start['speed']==0:break
  cmd('monitor input JOY1_FIRE_BUTTON 0');advance_fields(20,False);start=row('ready-after-contact')
  report['start_contact']=True
 assert start['speed']==0,start
 if clutch:assert start['rpm']>4000
 cmd('monitor input JOY1_FIRE_BUTTON 0');cmd('monitor input JOY1_2ND_BUTTON 1')
 advance_fields(60,False);accel=row('accelerated');assert accel['speed']>20,accel
 cmd('monitor input JOY1_2ND_BUTTON 0');advance_fields(30,False);coast=row('coasting');assert coast['speed']<accel['speed'],(accel,coast)
 cmd('monitor input JOY1_FIRE_BUTTON 1')
 for i in range(10):
  advance_fields(30,False);stopped=row('braking-'+str(i))
  if stopped['speed']==0:break
 assert stopped['speed']==0,stopped
 cmd('monitor input JOY1_FIRE_BUTTON 0');advance_fields(50,False);idle=row('idle');assert idle['speed']==0
 cmd('monitor input JOY1_2ND_BUTTON 1');advance_fields(50,False);restart=row('restarted');assert restart['speed']>20
 cmd('monitor mouse 8 0');advance_fields(10,False);right=row('steer-right')
 cmd('monitor mouse -16 0');advance_fields(10,False);left=row('steer-left')
 assert right['steering']!=left['steering'] and right['mouse_x']!=left['mouse_x']
 cmd('monitor mouse 8 0');cmd('monitor input JOY1_2ND_BUTTON 0');advance_fields(30,False);row('released')
 report['status']='passed';report['clutch_start']=clutch;save()
 cmd('delete');s.handle(g,'shot '+str(out/'controls.png'))
finally:
 try:
  if controls:
   try:controls.release_all()
   finally:(out/'actions.json').write_text(json.dumps(controls.actions,indent=2)+'\n')
 finally:
  (out/'capture.log').write_text('\n'.join(log))
  if s.g:s.g.p.kill()
  try:os.kill(int((r/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass
