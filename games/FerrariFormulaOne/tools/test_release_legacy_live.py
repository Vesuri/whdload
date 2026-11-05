from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='release-legacy-live';variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);b=Path(os.environ.get('FF1_BUILD',str(r/'tmp/build/production')))/'FerrariFormulaOne.slave';profiles=json.loads((r/'tmp/manifest/step3-profiles.json').read_text());os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=0 ConfigDelay=0'),DETERMINISTIC=os.environ.get('FF1_DETERMINISTIC','1'),FSUAE=str(r/'tmp/step3/fs-uae-q03-final'),KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),run_script=os.environ.get('RELEASE_RUN_SCRIPT','tools/run.sh'),run_dir='tmp/run/default/.run',profile_window=False);log=[]
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
 cmd('break *0x65174');cmd('ignore $bpnum 124');assert 'Breakpoint' in cmd('continue')
 memory=dump('input-start');build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];marker=memory.index(b'FF1B7PUBLICROOT');host=marker-hs['FF1PublicMarker']
 report={'profile':profile,'host':hex(host),'slave_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'custom2':0}
 fine=False;kind='legacy'
 def native(addr):return addr
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
  report['launch']=json.loads((r/'tmp/run/default/.run/launch.json').read_text());report['runtime_sha256']=hashlib.sha256((r/'tmp/run/default/.run/dh1/WHDLoad').read_bytes()).hexdigest()
  (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def snapshot(label):
  m=dump(label);v={'calendar':m[0x226c0:0x226ca].hex(),'session':m[0x226ca:0x226d4].hex(),'control_mode':struct.unpack_from('>H',m,0x1c1c2)[0],'difficulty':struct.unpack_from('>H',m,0x1c1c4)[0]};report[label]=v;save();return m,v
 def advance_fields(n,active=True):
  cmd('delete');cmd('break *0x2482a');cmd(f'ignore $bpnum {n-1}');assert 'Breakpoint' in cmd('continue')
 key('KEY_SPACE',0x40);until(0x65174);snapshot('takeover');key('KEY_K',0x27);until(0x65f48);snapshot('native-exit');cmd('monitor warp 1');advance_fields(2200,False);snapshot('after-exit');s.handle(g,'shot '+str(out/'after-exit.png'))
 import socket
 sockpath=str(r/'tmp/run/default/.run/q03-modal.sock')
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
 try:os.kill(int((r/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
