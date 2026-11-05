import os,subprocess,json,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(r.ROOT/'tools'))
from compare_h3 import compare
anchor=None
for mask in (0,0,1):
 pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
 if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
 out=Path('tmp/prof/w1-deferred-calibration' if anchor is None else f'tmp/prof/w1-deferred-entry-{mask}');assert not out.exists()
 env=dict(os.environ,MallocScribble='1',AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',EXTRA_ARGS='--slow_memory=1536 --uae_cpu_multiplier=2 --uae_cpu_speed=real --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true',WHD_ARGS=f'CUSTOM2={mask} CUSTOM5=512')
 if anchor is not None:env['BOOT_BREAK']=hex(anchor)
 print('entry control',mask,out,flush=True)
 with Path(f'tmp/w1-entry-control-fixed-{mask}.log').open('w') as f:subprocess.run([sys.executable,'tools/reach_flight.py','--out',str(out)],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
 if anchor is None:anchor=json.loads((out/'entry.json').read_text())['entry']['game_anchor']
p=Path('tmp/prof');a=p/'w1-deferred-entry-0';b=p/'w1-deferred-entry-1'
result=compare((a/'entry-h3.bin').read_bytes(),(b/'entry-h3.bin').read_bytes(),json.loads((a/'entry-steps.json').read_text()),json.loads((b/'entry-steps.json').read_text()));(p/'w1-deferred-entry-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('ranges','pointer_candidates')},flush=True)
