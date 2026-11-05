import os,subprocess,json,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,str(r.ROOT/'tools'))
from compare_h3 import compare
from check_disabled import check
from hook_ranges import ranges
base=Path('tmp/prof');state=step_log.collect();banks=[]
for i,(lo,hi) in enumerate(r.memory_regions()):
 p=base/f'w1-deferred-entry-0/off-memory-{i}.bin'
 r.command(f'gdb dump binary memory {p} {lo:#x} {hi:#x}');banks.append((lo,p.read_bytes()))
def read(addr,size):
 for lo,b in banks:
  if lo<=addr and addr+size<=lo+len(b):return b[addr-lo:addr-lo+size]
 raise ValueError('missing memory')
check(Path('tmp/game/RedBaron/data/sim').read_bytes(),state['sim'],read,ranges());print('All three off ranges unchanged',flush=True)
meta=json.loads((base/'w1-deferred-entry-0/entry.json').read_text())
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
out=base/'w1-deferred-entry-3';assert not out.exists()
env=dict(os.environ,MallocScribble='1',BOOT_BREAK=hex(meta['entry']['game_anchor']),AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',EXTRA_ARGS=meta['extra_args'],WHD_ARGS='CUSTOM2=3 CUSTOM5=512')
with Path('tmp/w1-deferred-entry-3.log').open('w') as f:subprocess.run([sys.executable,'tools/reach_flight.py','--out',str(out)],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
step_log.advance(8);state=step_log.collect();assert state['count']==8
r.command(f'gdb dump binary memory {out}/step8-h3.bin {state["h3"]:#x} {state["h3"]+0xbd0c:#x}')
(out/'step8.json').write_text(json.dumps(state,indent=2)+'\n')
a=base/'w1-deferred-entry-0'
for stem in ('entry','step8'):
 name='entry-steps.json' if stem=='entry' else 'step8.json'
 result=compare((a/f'{stem}-h3.bin').read_bytes(),(out/f'{stem}-h3.bin').read_bytes(),json.loads((a/name).read_text()),json.loads((out/name).read_text()))
 (out/f'{stem}-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(stem,result,flush=True)
