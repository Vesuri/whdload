from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='drive-manual';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=Path(os.environ['H4_BUILD'])/'FerrariFormulaOne.slave';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1 ConfigDelay=0'),DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae-q03-final'),KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),run_script=os.environ.get('RELEASE_RUN_SCRIPT','amiga/run.sh'),profile_window=False);log=[]
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
  report['launch']=json.loads((r/'amiga/.run/launch.json').read_text());report['runtime_sha256']=hashlib.sha256((r/'amiga/.run/dh1/WHDLoad').read_bytes()).hexdigest()
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def snapshot(label):
  m=dump(label);ctx=list(struct.unpack_from('>14I',m,probe+sym(fine_listing,'C1Context')))
  v={'context':ctx,'completed':struct.unpack_from('>I',m,probe+sym(fine_listing,'C1Context')+24)[0],'owned':(struct.unpack_from('>H',m,probe+sy['C4BlitOwned'])[0] if kind=='000' else 0),'calendar':m[native(0x226c0):native(0x226c0)+10].hex(),'session':m[native(0x226ca):native(0x226ca)+10].hex()}
  v['intena']=int(cmd('monitor irq-state').strip());report[label]=v;save();return m,v
 def advance_fields(n,active=True):
  cmd('delete');cmd(f'break *{probe+sym(fine_listing,"C1Vbl") if active else native(0x2482a)}');cmd(f'ignore $bpnum {n-1}');assert 'Breakpoint' in cmd('continue')
 cmd('monitor warp 0')
 key('KEY_SPACE',0x40)
 until(probe+sym(fine_listing,'C1Checkpoint'))
 memory,take=snapshot('takeover')
 key('KEY_K',0x27)
 report['phase']='tow-key-delivered';save();cmd('monitor warp 1')
 if fine:
  until(probe+sy['FF1FineExit'])
  until(native(0x65f48))
 else:
  until(probe+sym(fine_listing,'C1Exit'))
  until(native(0x65f48))
 memory,ex=snapshot('native-exit-restored')
 advance_fields(2200,False)
 memory,menu=snapshot('after-exit')
 assert menu['context']==ex['context']
 cmd('delete');s.handle(g,'shot '+str(out/'after-exit.png'))
 report['phase']='after-exit-observed';report['error']=val(f'*(unsigned int*){probe+sym(fine_listing,"error")}');save();print(report,flush=True)
 import socket
 sockpath=str(r/'amiga/.run/q03-modal.sock')
 if os.path.exists(sockpath):os.unlink(sockpath)
 server=socket.socket(socket.AF_UNIX);server.bind(sockpath);server.listen(1)
 print('Modal controls ready',sockpath,flush=True)
 while True:
  connection,_=server.accept();request=json.loads(s.read_request(connection));answer={}
  try:
   op=request['op']
   if op=='fields':advance_fields(request['count'],False)
   elif op=='move':
    for attempt in range(60):
     x=val(f'*(unsigned short*){native(0x24aa8)}');y=val(f'*(unsigned short*){native(0x24aaa)}');dx=request['x']-x;dy=y-request['y']
     if dx==dy==0:break
     cmd(f'monitor mouse {max(-16,min(16,dx))} {max(-16,min(16,dy))}');advance_fields(2,False)
    assert dx==dy==0,(x,y,request);answer={'x':x,'y':y}
   elif op=='click':
    cmd('monitor input JOY1_FIRE_BUTTON 1');advance_fields(4,False);cmd('monitor input JOY1_FIRE_BUTTON 0');advance_fields(request.get('settle',20),False)
   elif op=='shot':
    cmd('delete');answer['capture']=s.handle(g,'shot '+str(out/(request['label']+'.png')));_,answer['state']=snapshot(request['label'])
   elif op=='gdb':answer['reply']=cmd(request['command'])
   elif op=='exec':exec(request['code'],globals())
   elif op=='quit':answer={'status':'closing'}
   else:raise ValueError(op)
   report.setdefault('controls',[]).append({'request':request,'answer':answer});save()
  except Exception as e:answer={'error':repr(e)}
  connection.sendall((json.dumps(answer)+'\n').encode());connection.close()
  if request['op']=='quit':break
 server.close();os.unlink(sockpath)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
