#!/usr/bin/env python3
"""Fresh phase-10 fixed-window rendering comparison; breakpoint publications only."""
import argparse,json,os,re,shutil,subprocess,sys,time,socket
from harness import ROOT,server,command,snapshot,sha,listing
from race_capture import resolve
from timing_samples import capture
from check_units import check
p=argparse.ArgumentParser(description=__doc__);p.add_argument('name');p.add_argument('--preset',choices=['a500','a1200','a1200-030'],default='a500');p.add_argument('--fields',type=int,default=2000)
for k,v in [('c1',0),('c2',1),('c3',1),('c4',0),('c5',17)]:p.add_argument('--'+k,type=int,default=v)
a=p.parse_args();out=ROOT/'tmp/phase11'/a.name
if out.exists():p.error('fresh output required')
s=socket.socket(socket.AF_UNIX);s.settimeout(.2)
try:s.connect(server.sock)
except (FileNotFoundError,ConnectionRefusedError):pass
else:p.error('existing server; stop it first')
finally:s.close()
out.mkdir(parents=True);shutil.copyfile(ROOT/'tmp/phase8/math-vectors.json',out/'math-vectors.json');expected_units=json.loads((out/'math-vectors.json').read_text())['assertions'];opts=dict(C1=a.c1,C2=a.c2,C3=a.c3,C4=a.c4,C5=a.c5);active=bool(a.c1&2 or a.c3 or a.c4 or a.c5)
h4=0x1e548;anchor=h4+0xf6;slave=ROOT/'tmp/build/verify/TestDrive.Slave'
shutil.copyfile(slave,out/'slave.slave');shutil.copyfile(listing(slave),out/'slave.lst')
env=dict(os.environ,FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),TD_SETUP=a.preset,WARP='1',JOY0='none',SLAVE=str(out/'slave.slave'),WHD_ARGS=' '.join('CUSTOM'+k[1:]+'='+str(v if v<0x80000000 else v-0x100000000) for k,v in opts.items()),BOOT_BREAK=hex(anchor),BOOT_CONDITION=f'*(unsigned int*){h4:#x} == 0x4e55ffcc && *(unsigned short*){anchor:#x} == {0x4eb9 if active else 0x2b6c}')
env.pop('AMIGA_SETUP',None)
f=(out/'serve.log').open('w');proc=subprocess.Popen([sys.executable,str(ROOT/'tools/td.py'),'serve'],env=env,stdout=f,stderr=subprocess.STDOUT);ready=False
try:
 end=time.monotonic()+300
 while 'serving on' not in (out/'serve.log').read_text():
  if proc.poll() is not None:raise RuntimeError('server failed')
  if time.monotonic()>end:raise TimeoutError('race anchor not reached; inspect live process, do not restart')
  time.sleep(.5)
 ready=True;print(server.request('until '+hex(h4+0xfc)),flush=True)
 base,rr=resolve(out);assert rr['h4']==h4
 units=check((out/'code.bin').read_bytes(), expected_count=expected_units);(out/'units.json').write_text(json.dumps(units,indent=2)+'\n')
 frame=int(re.search(r'a5\s+(0x[0-9a-f]+)',command('info registers a5'))[1],16)
 (out/'capture.json').write_text(json.dumps(dict(base=base,regions=rr,options=opts,fields=a.fields,frame=frame,slave_sha256=sha(out/'slave.slave')),indent=2)+'\n')
 shutil.copyfile(ROOT/'tmp/run/default/.run/machine.json',out/'machine.json')
 (out/'hardware-start.txt').write_text(command('x/1hx 0xdff002\nx/1hx 0xdff01c'))
 from race_capture import state
 (out/'start-state.json').write_text(json.dumps(state(out,rr),indent=2)+'\n')
 assert a.fields==2000, 'two fixed 1000-field windows required'
 for window in range(2):
  folder=out/('window-'+str(window))
  subprocess.run([sys.executable,str(ROOT/'tools/swap_fields.py'),'1000',str(folder),str(out/'code.bin'),hex(base)],check=True)
  snapshot(folder/'end')
  (folder/'end-state.json').write_text(json.dumps(state(folder/'end',rr),indent=2)+'\n')
 (out/'hardware-end.txt').write_text(command('x/1hx 0xdff002\nx/1hx 0xdff01c'))
 snapshot(out/'end');print(server.request('shot '+str(out/'end.png')),flush=True)
 print(json.dumps(dict(name=a.name,units=units,fields=a.fields)),flush=True)
finally:
 if ready:server.request('quit');proc.wait(timeout=20)
 f.close()
 if ready:shutil.copyfile(ROOT/'tmp/run/default/.run/fsuae.log',out/'fsuae.log')
