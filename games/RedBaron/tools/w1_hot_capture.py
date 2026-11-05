"""Time the first natural later dashboard event, after the cache is populated."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--machine',choices=['a500','020','030'],required=True);p.add_argument('--mask',type=int,choices=[0,1,3],required=True);a=p.parse_args()
ref=Path(f'tmp/prof/w1-controlled-{a.machine}-{a.mask}');meta=json.loads((ref/'entry.json').read_text());census=json.loads((ref/'census/census.json').read_text())
start=min(e['step'] for e in census['events'] if e['kind']=='dirty' and e['step']>1)
out=Path(f'tmp/prof/w1-hot-{a.machine}-{a.mask}');assert not out.exists()
env=dict(os.environ,MallocScribble='1',BOOT_BREAK=hex(meta['entry']['game_anchor']),CPU=meta['cpu'],CHIP_KB=meta['chip_kb'],FAST_KB=meta['fast_kb'],EXTRA_ARGS=meta['extra_args'],WHD_ARGS=meta['whd_args'],AMIGA_MODEL='A1200' if a.machine=='020' else 'A500')
if a.machine=='020':env['KICKSTART']=os.environ['KICKSTART_A1200']
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
with Path(f'tmp/w1-hot-{a.machine}-{a.mask}.log').open('w') as f:subprocess.run([sys.executable,'tools/reach_flight.py','--out',str(out)],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
assert json.loads((out/'entry.json').read_text())['slave_sha256']=='5c0918ccbccb27ad301478873e1aeab8398f057211b2749ce7d16fe949f23475'
step_log.advance(start);state=step_log.collect();(out/'checkpoint.json').write_text(json.dumps(state,indent=2)+'\n')
if a.machine=='030':
 subprocess.run([sys.executable,'tools/w1_clock.py','--entry',str(out),'--mask',str(a.mask),'--step',str(start+5),'--out',str(out/'clock.json')],check=True)
else:subprocess.run([sys.executable,'tools/capture_current.py','--out',str(out/'window'),'--fields',str(100 if a.machine=='a500' else 40)],check=True)
(out/'complete.json').write_text(json.dumps({'complete':True,'machine':a.machine,'mask':a.mask,'start_step':start,'selection':'First later dirty event in this setting’s completed native census; routine-cost sample, not a fixed-state A/B'},indent=2)+'\n');print('COMPLETE',out,flush=True)
