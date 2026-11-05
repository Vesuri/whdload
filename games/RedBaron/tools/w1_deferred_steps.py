import os,subprocess,json,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,str(r.ROOT/'tools'))
from compare_h3 import compare
base=Path('tmp/prof')
def snap(mask):
 out=base/f'w1-deferred-entry-{mask}'
 step_log.advance(8);state=step_log.collect();assert state['count']==8
 r.command(f'gdb dump binary memory tmp/build/w1-step-h3.bin {state["h3"]:#x} {state["h3"]+0xbd0c:#x}')
 (out/'step8-h3.bin').write_bytes(Path('tmp/build/w1-step-h3.bin').read_bytes());(out/'step8.json').write_text(json.dumps(state,indent=2)+'\n')
snap(1)
meta=json.loads((base/'w1-deferred-entry-0/entry.json').read_text())
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
out=base/'w1-deferred-step-control-0';assert not out.exists()
env=dict(os.environ,MallocScribble='1',BOOT_BREAK=hex(meta['entry']['game_anchor']),AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',EXTRA_ARGS=meta['extra_args'],WHD_ARGS='CUSTOM2=0 CUSTOM5=512')
with Path('tmp/w1-deferred-step-control-0.log').open('w') as f:subprocess.run([sys.executable,'tools/reach_flight.py','--out',str(out)],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
snap(0)
a=base/'w1-deferred-entry-0';b=base/'w1-deferred-entry-1'
result=compare((a/'step8-h3.bin').read_bytes(),(b/'step8-h3.bin').read_bytes(),json.loads((a/'step8.json').read_text()),json.loads((b/'step8.json').read_text()))
(base/'w1-deferred-step8-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
