"""Normal-build PS entry; native keyboard control is supplied by the matrix driver."""
import argparse, hashlib, json, os, re, struct, subprocess, sys, time
from pathlib import Path
import route_status as r
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from completion_machines import MACHINES, environment
from hunks import read_hunks
p=argparse.ArgumentParser();p.add_argument('machine',choices=MACHINES);p.add_argument('mask',type=lambda s:int(s,0));p.add_argument('out',type=Path);p.add_argument('--entry-only',action='store_true');a=p.parse_args();os.chdir(ROOT)
if a.out.exists():raise SystemExit('Refusing overwrite')
pid=ROOT/'tmp/run/default/.run/fsuae.pid'
if pid.exists():
 z=subprocess.run(['ps','-p',pid.read_text().strip(),'-o','stat=,command='],capture_output=True,text=True)
 if z.returncode==0 and not z.stdout.lstrip().startswith('Z'):raise SystemExit('Existing emulator must be inspected and quit first: '+z.stdout)
a.out.mkdir(parents=True)
developer=os.environ.get('BENCH_DEVELOPER')=='1'
if not developer and a.mask not in (0,1):raise ValueError('Normal build accepts only player switch 0/1')
env=environment(a.machine,a.mask,functional=os.environ.get("BENCH_FUNCTIONAL")=="1");env.update(WARP='1',DETERMINISTIC='1',JOY0='none',JOY0_MODE='nothing',JOY1='none',VERIFY='0',DEVELOPER='1' if developer else '0')
env.pop('BOOT_BREAK',None)
if os.environ.get("BENCH_IMAGE_MODE")=="1": env["EXTRA_ARGS"]="--hard_drive_0=../tmp/prof/cockpit-line-disks/boot.hdf --hard_drive_1=../tmp/prof/cockpit-line-disks/game.hdf"
if 'BENCH_CUSTOM3' in os.environ:env['WHD_ARGS']+=' CUSTOM3='+str(int(os.environ['BENCH_CUSTOM3']))
if os.environ.get('BENCH_OMIT_CUSTOM2')=='1':
 assert not developer and a.mask==0
 env['WHD_ARGS']=re.sub(r'\bCUSTOM2=\d+\s*','',env['WHD_ARGS'])
frozen=os.environ.get('BENCH_FROZEN_SLAVE')
if not frozen:subprocess.run(['bash','tools/build.sh'],env=env,check=True)
slave=Path(frozen).resolve() if frozen else ROOT/'tmp/build'/('RedBaron-developer.slave' if developer else 'RedBaron.slave')
env['SLAVE']=str(slave)
(a.out/'slave.slave').write_bytes(slave.read_bytes())
(a.out/'slave.lst').write_bytes((slave.parent/'slave.lst' if frozen else slave.with_suffix('.slave.lst')).read_bytes())
with (a.out/'serve.log').open('w') as log:
 server=subprocess.Popen([sys.executable,'tools/redbaron.py','serve'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
for _ in range(120):
 if server.poll() is not None:raise RuntimeError('Server exited')
 try:
  if 'serving on' in (a.out/'serve.log').read_text():break
 except FileNotFoundError:pass
 time.sleep(1)
else:raise TimeoutError('Server startup')

def locate(name,off,targets):
 for attempt in range(30):
  r.command('stop')
  for lo,hi in r.memory_regions():
   path=a.out/f'locate-{lo:x}.bin';r.command(f'gdb dump binary memory {path} {lo:#x} {hi:#x}')
   if not path.exists():continue
   b=path.read_bytes()
   pos=0
   while True:
    pos=b.find(b'\x4e\xf9',pos)
    if pos<0:break
    if pos+6*len(targets)<=len(b):
     base=struct.unpack_from('>I',b,pos+2)[0]-targets[0]
     if base>0 and all(b[pos+6*j:pos+6*j+2]==b'\x4e\xf9' and struct.unpack_from('>I',b,pos+6*j+2)[0]==base+t for j,t in enumerate(targets)) and base+off==lo+pos:
      print(name,hex(base),flush=True);return base
    pos+=2
  r.command('cont');time.sleep(2)
 raise TimeoutError('Cannot locate '+name)

ps=locate('ps',0x15b3a,[0x2b4f4,0x26e8,0x7e24])
if a.entry_only:
 (a.out/'ps-ready.json').write_text(json.dumps(dict(ps=ps,environment=env)))
 print('PS READY',flush=True);raise SystemExit(0)
raise SystemExit('Use completion_matrix_case.py for debugger input and flight capture')
