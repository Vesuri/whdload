import json,subprocess,os,sys
from pathlib import Path
root=Path('tmp');rows=[]
for n in range(1,5):
 ref=root/f'c-geometry-reuse-exact-period{n}-state';out=root/f'c-passive-period{n}-state'
 env=dict(os.environ,SLAVE=str((root/f'c-geometry-reuse-exact-period{n}-build/RoadRash-verify.slave').resolve()),RR_TAPE='1',RR_TAPE_PATH=str(Path('tools/fixtures/c-attacks.json').resolve()),RR_CAPTURE='1457',RR_EVENTS_TEST='1',EXTRA_ARGS='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false')
 subprocess.run([sys.executable,'tools/passive_invoke_c.py','tools/step_c.py',str(out)],env=env,check=True,timeout=180)
 subprocess.run([sys.executable,'tools/compare_short_c.py',str(ref),str(out)],check=True)
 rows.append(json.loads((out/'comparison.json').read_text()));(root/'passive-diagnostic-comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
