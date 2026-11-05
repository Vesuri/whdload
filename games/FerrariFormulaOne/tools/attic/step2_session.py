#!/usr/bin/env python3
"""Native emulator input exploration with an append-only action log and snapshots."""
from pathlib import Path
import os,sys,json,signal,socket,re,hashlib,shutil
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1];os.chdir(root)
s=Server('ff1native',root=str(root),profile_window=False)
if sys.argv[1]!='serve':print(s.request(' '.join(sys.argv[1:])),end='');sys.exit()
name=sys.argv[2];out=root/'tmp/step2'/name;out.mkdir(parents=True,exist_ok=True)
os.environ.update(SLAVE=str(root/'tmp/build/step2/probe-s0-p1-w0.slave'),FSUAE=str(root/'tmp/step2/emulator-build/fs-uae'),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=0',DETERMINISTIC='1',JOY0='mouse')
log=[];actions=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=120);log.append(c+'\n'+v);(out/'capture.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def until(a):
  cmd('delete');cmd(f'break *{a:#x}');v=cmd('continue');assert 'Breakpoint' in v,v
 def fields(n):
  assert 1<=n<=10000
  cmd('delete');cmd('break *0x24824')
  if n>1:cmd(f'ignore $bpnum {n-1}')
  v=cmd('continue');assert 'Breakpoint' in v,v
 def state():
  return {k:val(f'*(unsigned short*){a}') for k,a in dict(native_fields=0x24ad2,x=0x24aa8,y=0x24aaa,demo=0x1bee8,mode=0x1c1c2,difficulty=0x1c1c4,speed=0x2275a,segment=0x6a60a,buttons=0x66f92,countdown=0x66f94,gear=0x66c3c).items()}
 def event(k,v):
  r=cmd(f'monitor input {k} {v}');assert 'error' not in r.lower(),r
 def click(x,y):
  # Native hardware movement; closed loop deals with device scaling and wrapping.
  for _ in range(40):
   cx=val('*(short*)0x24aa8');cy=val('*(short*)0x24aaa');dx=x-cx;dy=cy-(199-y)
   if abs(dx)<=1 and abs(dy)<=1:break
   cmd(f'monitor mouse {max(-32,min(32,dx))} {max(-32,min(32,dy))}');fields(3)
  else:raise RuntimeError('mouse target not reached')
  event('JOY1_FIRE_BUTTON',1);fields(8);event('JOY1_FIRE_BUTTON',0);fields(8)
 until(0x65174);print('native session at race loop',state(),flush=True)
 if os.path.exists(s.sock):os.unlink(s.sock)
 sock=socket.socket(socket.AF_UNIX);sock.bind(s.sock);sock.listen(1)
 shutil.copy(root/'amiga/.run/launch.json',out/'launch.json')
 while True:
  c,_=sock.accept();line=s.read_request(c);parts=line.split();op=parts[0]
  try:
   if op=='fields':fields(int(parts[1]))
   elif op=='event':event(parts[1],int(parts[2],0))
   elif op=='key':
    event(parts[1],1);fields(4);event(parts[1],0);fields(4)
   elif op=='mouse':cmd('monitor mouse '+' '.join(parts[1:]));fields(3)
   elif op=='click':click(int(parts[1]),int(parts[2]))
   elif op=='until':until(int(parts[1],0))
   elif op=='warp':cmd('monitor warp '+parts[1])
   elif op=='gdb':reply=cmd(line[4:]);c.sendall(reply.encode());c.close();continue
   elif op=='shot':
    label=parts[1];assert re.fullmatch('[a-z0-9-]+',label)
    cmd('delete');s.handle(g,'shot '+str(out/f'{label}.png'))
    cmd(f'dump binary memory tmp/step2/{name}/{label}.bin 0 0x80000')
   elif op=='quit':
    c.sendall(b'closed\n');c.close();break
   elif op!='state':raise ValueError(op)
   st=state();actions.append({'command':line,'after':st});(out/'actions.json').write_text(json.dumps(actions,indent=2)+'\n');reply=json.dumps(st)
  except Exception as e:reply='ERROR '+str(e)
  c.sendall((reply+'\n').encode());c.close()
finally:
 if s.g:
  s.g.p.kill()
  try:os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except ProcessLookupError:pass
