"""Short bank/dense performance window, using a prior same-build scene anchor."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--machine',choices=['a500','020','030'],required=True);p.add_argument('--scene',choices=['bank','dense'],required=True);p.add_argument('--mask',type=int,choices=[0,1,3],required=True);a=p.parse_args()
ref=Path(f'tmp/prof/w1-scene-twins-{a.machine}-{a.scene}');meta=json.loads((ref/'entry.json').read_text());assert meta['slave_sha256']=='5c0918ccbccb27ad301478873e1aeab8398f057211b2749ce7d16fe949f23475'
out=Path(f'tmp/prof/w1-scene-{a.machine}-{a.scene}-{a.mask}');assert not out.exists()
env=dict(os.environ,MallocScribble='1',BOOT_BREAK=hex(meta['entry']['game_anchor']),CPU=meta['cpu'],CHIP_KB=meta['chip_kb'],FAST_KB=meta['fast_kb'],EXTRA_ARGS=meta['extra_args'],WHD_ARGS=f'CUSTOM2={a.mask} CUSTOM5={512+(2 if a.scene=="bank" else 20)}'+(' MMU' if a.machine=='030' else ''),AMIGA_MODEL='A1200' if a.machine=='020' else 'A500')
if a.machine=='020':env['KICKSTART']=os.environ['KICKSTART_A1200']
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
with Path(f'tmp/w1-scene-{a.machine}-{a.scene}-{a.mask}.log').open('w') as f:subprocess.run([sys.executable,'tools/reach_flight.py','--out',str(out)],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
assert json.loads((out/'entry.json').read_text())['slave_sha256']==meta['slave_sha256']
step_log.advance(24 if a.scene=='bank' else 8);state=step_log.collect();(out/'checkpoint.json').write_text(json.dumps(state,indent=2)+'\n')
r.command(f'gdb dump binary memory {out}/checkpoint-h3.bin {state["h3"]:#x} {state["h3"]+0xbd0c:#x}')
subprocess.run([sys.executable,'tools/capture_current.py','--out',str(out/'window'),'--fields',str({'a500':100,'020':40,'030':20}[a.machine])],check=True)
(out/'complete.json').write_text(json.dumps({'complete':True,'machine':a.machine,'scene':a.scene,'mask':a.mask},indent=2)+'\n');print('COMPLETE',out,flush=True)
