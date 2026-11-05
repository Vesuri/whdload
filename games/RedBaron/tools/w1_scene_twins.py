"""Sequential correctness coverage; run only after the measurement queue exits."""
import argparse,os,sys,subprocess,json
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,str(r.ROOT/'tools'))
from mirror_checks import read_checks
p=argparse.ArgumentParser();p.add_argument('--machine',choices=['a500','020','030'],required=True);p.add_argument('--scene',choices=['bank','dense'],required=True);p.add_argument('--mask',type=int,choices=[2,3],default=3);a=p.parse_args()
out=Path(f'tmp/prof/w1-scene-twins-{a.machine}-{a.scene}'+('' if a.mask==3 else f'-{a.mask}'));assert not out.exists()
common=' --uae_cpu_speed=real --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true'
env=dict(os.environ,MallocScribble='1',WHD_ARGS=f'CUSTOM2={a.mask} CUSTOM5={864+(2 if a.scene=="bank" else 20)+(8 if a.machine=="030" else 0)}');env.pop('BOOT_BREAK',None)
if a.machine=='a500':env.update(AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',EXTRA_ARGS='--slow_memory=1536 --uae_cpu_multiplier=2'+common)
elif a.machine=='020':env.update(AMIGA_MODEL='A1200',KICKSTART=os.environ['KICKSTART_A1200'],CPU='68EC020',CHIP_KB='2048',FAST_KB='8192',EXTRA_ARGS='--slow_memory=0 --uae_cpu_multiplier=4'+common)
else:env.update(AMIGA_MODEL='A500',CPU='68030',CHIP_KB='2048',FAST_KB='8192',EXTRA_ARGS='--slow_memory=0 --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000 --uae_cpu_data_cache=true'+common,WHD_ARGS=env['WHD_ARGS']+' MMU')
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
with Path(f'tmp/w1-scene-twins-{a.machine}-{a.scene}.log').open('w') as f:subprocess.run([sys.executable,'tools/reach_flight.py','--out',str(out)],env=env,check=True,stdout=f,stderr=subprocess.STDOUT)
assert json.loads((out/'entry.json').read_text())['slave_sha256']=='5c0918ccbccb27ad301478873e1aeab8398f057211b2749ce7d16fe949f23475'
step_log.advance(40);state=step_log.collect();assert state['count']==40
(out/'step40.json').write_text(json.dumps(state,indent=2)+'\n')
subprocess.run([sys.executable,'tools/cache_status.py','--entry',str(out),'--out',str(out/'cache-status.json')],check=True)
checks=read_checks((r.ROOT/'tmp/build/route-ram.bin').read_bytes());(out/'mirror-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(out/'checks-memory.bin').write_bytes((r.ROOT/'tmp/build/route-ram.bin').read_bytes())
z=json.loads((out/'cache-status.json').read_text());assert z['route']['inflight']==1 and z['checks']['lifecycle']==1 and z['checks']['build_twins']>=5 and z['checks']['pixel_twins']>0
if a.machine=='030':
 subprocess.run([sys.executable,'tools/paint_log.py','--out',str(out/'paint.json')],check=True)
 paint=json.loads((out/'paint.json').read_text());assert paint['cacr_valid'] and paint['raw_cacr']==0x2111
print(r.command('shot '+str((out/'step40.png').resolve())),flush=True)
(out/'complete.json').write_text(json.dumps({'complete':True,'machine':a.machine,'scene':a.scene,'mirror':checks,'cache':z['checks']},indent=2)+'\n');print('COMPLETE',out,checks,flush=True)
