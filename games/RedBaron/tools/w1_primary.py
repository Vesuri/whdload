#!/usr/bin/env python3
"""One sequential frozen-build W1 measurement case; no concurrent captures."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from completion_machines import MACHINES, environment
ROOT=Path(__file__).resolve().parents[1]
EXPECTED='158247428d5de8b4bbe907bae3760a2c6c0e65ad7f3fcb37d8fc87b16883ba03'
p=argparse.ArgumentParser();p.add_argument('--machine',choices=MACHINES,required=True);p.add_argument('--mask',type=int,choices=[0,1,3],required=True);a=p.parse_args();os.chdir(ROOT)
base=Path('tmp/prof');out=base/f'w1-matrix-{a.machine}-{a.mask}'
if out.exists():raise SystemExit('Refusing to overwrite an existing case')
env=environment(a.machine,a.mask)
def owned():
 f=ROOT/'tmp/run/default/.run/fsuae.pid'
 if not f.exists():return
 z=subprocess.run(['ps','-p',f.read_text().strip(),'-o','command='],capture_output=True,text=True)
 if z.returncode==0 and f'--base_dir={ROOT/"tmp/run/default/.run/fsuae"}' not in z.stdout:raise RuntimeError('Recorded PID is not this worktree emulator')
def run(script,*args,log=None):
 print(a.machine,a.mask,script,' '.join(map(str,args)),flush=True)
 cmd=[sys.executable,'tools/'+script,*map(str,args)]
 if log:
  with Path(log).open('w') as f:subprocess.run(cmd,env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
 else:subprocess.run(cmd,env=env,check=True)
anchor_file=base/'w1-anchors.json';anchors=json.loads(anchor_file.read_text()) if anchor_file.exists() else {}
if a.machine not in anchors:
 cal=base/f'w1-calibration-{a.machine}';owned();env.pop('BOOT_BREAK',None)
 run('reach_flight.py','--out',cal,log=Path('tmp')/f'w1-calibration-{a.machine}.log')
 meta=json.loads((cal/'entry.json').read_text());assert meta['slave_sha256']==EXPECTED
 anchors[a.machine]=dict(anchor=meta['entry']['game_anchor'],sha256=EXPECTED)
 anchor_file.write_text(json.dumps(anchors,indent=2)+'\n')
assert anchors[a.machine]['sha256']==EXPECTED
env['BOOT_BREAK']=hex(anchors[a.machine]['anchor']);owned()
run('reach_flight.py','--out',out,log=Path('tmp')/f'w1-matrix-{a.machine}-{a.mask}.log')
meta=json.loads((out/'entry.json').read_text());assert meta['slave_sha256']==EXPECTED
assert meta['entry']['game_anchor']==anchors[a.machine]['anchor']
fields=100 if a.machine=='a500' else 40 if a.machine=='020' else 20
run('capture_current.py','--out',out/'event','--fields',fields)
def snapshot(step):
 if step_log.collect()['count']<step:step_log.advance(step)
 state=step_log.collect();assert state['count']==step
 (out/f'step{step}.json').write_text(json.dumps(state,indent=2)+'\n')
 r.command(f'gdb dump binary memory {out}/h3-step{step}.bin {state["h3"]:#x} {state["h3"]+0xbd0c:#x}')
snapshot(8)
run('capture_current.py','--out',out/'steady-0','--fields',fields)
if a.machine=='a500':run('capture_current.py','--out',out/'steady-1','--fields',50)
snapshot(20)
run('dashboard_census.py','--out',out/'census')
(out/'complete.json').write_text(json.dumps(dict(machine=a.machine,mask=a.mask,sha256=EXPECTED,complete=True),indent=2)+'\n')
print('COMPLETE',out,flush=True)
