import json,os,subprocess,sys
from pathlib import Path
import route_status as r,step_log
ref=Path('tmp/prof/w1-controlled-030-0');meta=json.loads((ref/'entry.json').read_text());out=Path('tmp/prof/w2-pipeline-030');assert not out.exists()
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
env=dict(os.environ,MallocScribble='1',AMIGA_MODEL='A500',CPU=meta['cpu'],CHIP_KB=meta['chip_kb'],FAST_KB=meta['fast_kb'],EXTRA_ARGS=meta['extra_args'],WHD_ARGS='CUSTOM2=0 CUSTOM5=512 MMU');env.pop('BOOT_BREAK',None)
with Path('tmp/w2-pipeline-030.log').open('w') as log:subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
step_log.advance(120);(out/'step120.json').write_text(json.dumps(step_log.collect(),indent=2)+'\n')
subprocess.run([sys.executable,'tools/w2_pipeline_clock.py','--entry',str(out),'--mask','0','--step','126','--out',str(out/'clock.json')],check=True)
subprocess.run([sys.executable,'tools/routine_wall_time.py',str(out/'clock.json'),'--first-step','120','--last-step','125','--out',str(out/'summary.json')],check=True)
