#!/usr/bin/env python3
"""One sequential frozen-build W1 measurement case; no concurrent captures."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import route_status as r,step_log
ROOT=Path(__file__).resolve().parents[1]
EXPECTED='99c490efbde1b312d42c77ffeb3b7d348cacb6364b402fa9d15803765485d313'
p=argparse.ArgumentParser();p.add_argument('--machine',choices=['a500','020','030'],required=True);p.add_argument('--mask',type=int,choices=[0,1,3],required=True);a=p.parse_args();os.chdir(ROOT)
base=Path('tmp/prof');out=base/f'w1-controlled-{a.machine}-{a.mask}'
if out.exists():raise SystemExit('Refusing to overwrite an existing case')
env=dict(os.environ,MallocScribble='1',WHD_ARGS=f'CUSTOM2={a.mask} CUSTOM5=512')
flags=' --uae_cpu_speed=real --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true'
if a.machine=='a500':
 env.update(AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',EXTRA_ARGS='--slow_memory=1536 --uae_cpu_multiplier=2'+flags)
elif a.machine=='020':
 env.update(AMIGA_MODEL='A1200',KICKSTART=os.environ['KICKSTART_A1200'],CPU='68EC020',CHIP_KB='2048',FAST_KB='8192',EXTRA_ARGS='--slow_memory=0 --uae_cpu_multiplier=4'+flags)
else:
 env.update(AMIGA_MODEL='A500',CPU='68030',CHIP_KB='2048',FAST_KB='8192',EXTRA_ARGS='--slow_memory=0 --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000 --uae_cpu_data_cache=true'+flags,WHD_ARGS=env['WHD_ARGS']+' MMU')
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
anchor_file=base/'w1-controlled-anchors.json';anchors=json.loads(anchor_file.read_text()) if anchor_file.exists() else {}
if a.machine not in anchors:
 cal=base/f'w1-controlled-calibration-{a.machine}';owned();env.pop('BOOT_BREAK',None)
 run('reach_flight.py','--out',cal,log=Path('tmp')/f'w1-controlled-calibration-{a.machine}.log')
 meta=json.loads((cal/'entry.json').read_text());assert meta['slave_sha256']==EXPECTED
 anchors[a.machine]=dict(anchor=meta['entry']['game_anchor'],sha256=EXPECTED)
 anchor_file.write_text(json.dumps(anchors,indent=2)+'\n')
assert anchors[a.machine]['sha256']==EXPECTED
env['BOOT_BREAK']=hex(anchors[a.machine]['anchor']);owned()
run('reach_flight.py','--out',out,log=Path('tmp')/f'w1-controlled-{a.machine}-{a.mask}.log')
meta=json.loads((out/'entry.json').read_text());assert meta['slave_sha256']==EXPECTED
assert meta['entry']['game_anchor']==anchors[a.machine]['anchor']
fields={'a500':100,'020':40,'030':20}[a.machine]
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
owned()
run('reach_flight.py','--no-shot','--out',out/'census-entry',log=Path('tmp')/f'w1-controlled-census-{a.machine}-{a.mask}.log')
assert json.loads((out/'census-entry/entry.json').read_text())['slave_sha256']==EXPECTED
run('dashboard_census.py','--out',out/'census')
(out/'complete.json').write_text(json.dumps(dict(machine=a.machine,mask=a.mask,sha256=EXPECTED,complete=True),indent=2)+'\n')
print('COMPLETE',out,flush=True)
