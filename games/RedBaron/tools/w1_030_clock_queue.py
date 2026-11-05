"""Whole-call clocks for cached CPU; run after other capture controllers exit."""
import json,os,subprocess,sys
from pathlib import Path
import route_status as r
for mask in (0,1,3):
 ref=Path(f'tmp/prof/w1-controlled-030-{mask}');meta=json.loads((ref/'entry.json').read_text());out=Path(f'tmp/prof/w1-clock-030-{mask}');assert not out.exists()
 env=dict(os.environ,MallocScribble='1',BOOT_BREAK=hex(meta['entry']['game_anchor']),AMIGA_MODEL='A500',CPU=meta['cpu'],CHIP_KB=meta['chip_kb'],FAST_KB=meta['fast_kb'],EXTRA_ARGS=meta['extra_args'],WHD_ARGS=meta['whd_args'])
 pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
 if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
 with Path(f'tmp/w1-clock-030-{mask}.log').open('w') as f:subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
 assert json.loads((out/'entry.json').read_text())['slave_sha256']=='5c0918ccbccb27ad301478873e1aeab8398f057211b2749ce7d16fe949f23475'
 subprocess.run([sys.executable,'tools/w1_clock.py','--entry',str(out),'--mask',str(mask),'--step','120','--out',str(out/'clock.json')],check=True)
 (out/'complete.json').write_text(json.dumps({'complete':True,'mask':mask},indent=2)+'\n');print('CLOCK COMPLETE',mask,flush=True)
