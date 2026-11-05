import json,os,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);w=json.loads((p/'window.json').read_text())
if os.environ.get('P6_CUSTOM2')=='0':subprocess.run([sys.executable,'tools/check_disabled.py',str(p),'--render-only'],check=True)
subprocess.run([sys.executable,'tools/p3_cache_check.py',str(p)],check=True)
for name in ['discovery.bin','live-discovery.bin']:(p/name).unlink(missing_ok=True)
print('Field-derived steps/s',w['consumed_steps']*w['start']['sim_time_field_hz']/(w['end']['sim_clock_fields']-w['start']['sim_clock_fields']))
