"""Local validation driver: ordinary/zero-delay gates and fast-core timing sanity."""
import os,sys,json,subprocess
from pathlib import Path
from capture_demo import ROOT,main
from machine_profiles import PROFILES
os.chdir(ROOT)
for name,slave in [('normal','step1-normal.slave'),('slow-zero','HardDrivin-slow-manual.slave')]:
 subprocess.run([sys.executable,str(ROOT/'tools/capture_disabled.py'),'tmp/prof/disabled-'+name+'-final','--slave',str(ROOT/'tmp/build'/slave)],check=True)
# Ephemeral validation profile; not part of the benchmark matrix.
PROFILES['a4000-040-8-check']=('A4000','68040-NOMMU',2048,8192,0,8000000,'swaps')
sys.argv=['capture_demo.py','tmp/prof/clock-040-8-check','--profile','a4000-040-8-check','--fields','100'];main()
p=ROOT/'tmp/prof'
low=json.loads((p/'clock-040-8-check/counter.json').read_text())['swaps']
high=json.loads((p/'matrix-a4000-040-25-smoke/counter.json').read_text())['swaps']
r=dict(fields=100,mhz8_swaps=low,mhz25_swaps=high,frequency_sensitive=low<high)
(p/'step1-clock-sanity.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
assert r['frequency_sensitive'],'Fast-core timing is not yet validated'
