#!/usr/bin/env python3
"""Boot W5 using the already-validated CPU configurations."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('machine',choices=['a500','020','030']);p.add_argument('mask',type=int);p.add_argument('out',type=Path);p.add_argument('--immediate',action='store_true');p.add_argument('--stress',action='store_true');p.add_argument('--twins',action='store_true');p.add_argument('--scene',choices=['steady','bank','dense'],default='steady');a=p.parse_args()
ref=Path('tmp/prof')/('w2-combined-030-0-r2' if a.machine=='030' else f'w2-combined-{a.machine}-0')
m=json.loads((ref/'entry.json').read_text())
base=Path.cwd()/'tmp/run/default/.run/fsuae';pid=Path('tmp/run/default/.run/fsuae.pid')
if pid.exists():
 result=subprocess.run(['ps','-p',pid.read_text().strip(),'-o','command='],capture_output=True,text=True)
 if result.returncode==0: assert f'--base_dir={base}' in result.stdout
assert not (a.out/'entry.json').exists()
env=dict(os.environ,MallocScribble='1',CPU=m['cpu'],CHIP_KB=m['chip_kb'],FAST_KB=m['fast_kb'],EXTRA_ARGS=m['extra_args'],AMIGA_MODEL='A1200' if a.machine=='020' else 'A500',WHD_ARGS=f'CUSTOM2={a.mask} CUSTOM5={(66048 if a.twins else (0 if a.immediate else 512))|(131072 if a.stress else 0)|{'steady':0,'bank':2,'dense':20}[a.scene]}'+(' MMU' if a.machine=='030' else ''))
env.pop('BOOT_BREAK',None)
env['BOOT_TIMEOUT']='240'
subprocess.run(['bash','tools/build.sh'],env=dict(env,VERIFY='1'),check=True)

assert hashlib.sha256(Path('tmp/build/RedBaron-verify.slave').read_bytes()).hexdigest()=='3e3ddb5ccacfbb072658847716dc8d3b9eba3c941ec2e5587af0086437e2eae3'

# Use only a directly observed anchor for this exact build/machine. A larger
# slave can move its allocation, so old-build load bases are not reusable.
cal=Path(f'tmp/w5-anchor-{a.machine}.json')
if cal.exists():
 c=json.loads(cal.read_text())
 assert c['sha256']==hashlib.sha256(Path('tmp/build/RedBaron-verify.slave').read_bytes()).hexdigest()
 env['BOOT_BREAK']=hex(c['anchor'])
if a.machine=='020':env['KICKSTART']=os.environ['KICKSTART_A1200']
subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(a.out)],env=env,check=True)
m=json.loads((a.out/'entry.json').read_text())


cal.write_text(json.dumps(dict(sha256=m['slave_sha256'],anchor=m['entry']['game_anchor']))+'\n')
