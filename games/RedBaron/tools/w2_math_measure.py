"""Frozen W2 build: bounded same-build steady costs, swap rate and state on each CPU."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,str(r.ROOT/'tools'))
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import call_costs,census_window,display_ownership
EXPECTED='1456f8d5b84cf787f3429b7ae6580fcc88ce94903d604bbb3d339610f85853b3'
p=argparse.ArgumentParser();p.add_argument('--machine',choices=['a500','020','030'],required=True);p.add_argument('--mask',type=int,choices=[0,60],required=True);p.add_argument('--suffix',default='');a=p.parse_args()
out=Path(f'tmp/prof/w2-math-{a.machine}-{a.mask}{a.suffix}');assert not out.exists()
ref=Path(f'tmp/prof/w2-combined-twins-{a.machine}-bank');meta=json.loads((ref/'entry.json').read_text());assert meta['slave_sha256']==EXPECTED
common=' --uae_cpu_speed=real --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true'
env=dict(os.environ,MallocScribble='1',WHD_ARGS=f'CUSTOM2={a.mask} CUSTOM5=512'+(' MMU' if a.machine=='030' else ''),BOOT_BREAK=hex(meta['entry']['game_anchor']),CPU=meta['cpu'],CHIP_KB=meta['chip_kb'],FAST_KB=meta['fast_kb'],EXTRA_ARGS=meta['extra_args'],AMIGA_MODEL='A1200' if a.machine=='020' else 'A500')
if a.machine=='020':env['KICKSTART']=os.environ['KICKSTART_A1200']
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
with Path(f'tmp/w2-math-{a.machine}-{a.mask}{a.suffix}.log').open('w') as log:subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assert json.loads((out/'entry.json').read_text())['slave_sha256']==EXPECTED
step_log.advance(8)
def snapshot(step):
 state=step_log.collect();assert state['count']==step
 (out/f'step{step}.json').write_text(json.dumps(state,indent=2)+'\n')
 r.command(f'gdb dump binary memory {out}/h3-step{step}.bin {state["h3"]:#x} {state["h3"]+0xbd0c:#x}')
 return state
s=snapshot(8)
subprocess.run([sys.executable,'tools/w2_math_clock.py','--group','math','--entry',str(out),'--mask',str(a.mask),'--step','14','--out',str(out/'math-clock.json')],check=True)
subprocess.run([sys.executable,'tools/routine_wall_time.py',str(out/'math-clock.json'),'--first-step','8','--last-step','13','--out',str(out/'math-summary.json')],check=True)
