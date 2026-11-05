"""Cache-only cached-CPU timing and independent full-flight correctness, serially."""
import json,re,subprocess,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(r.ROOT/'tools'))
from mirror_checks import read_checks
from check_disabled import check
from hook_ranges import ranges
subprocess.run([sys.executable,'tools/w1_030_cache_only.py'],check=True)
subprocess.run([sys.executable,'tools/w1_scene_twins.py','--machine','030','--scene','bank','--mask','2'],check=True)
case=Path('tmp/prof/w1-scene-twins-030-bank-2')
subprocess.run([sys.executable,'tools/dashboard_census.py','--out',str(case/'full-flight')],check=True)
subprocess.run([sys.executable,'tools/cache_status.py','--entry',str(case),'--out',str(case/'full-cache-status.json')],check=True)
status=json.loads((case/'full-cache-status.json').read_text());assert status['checks']['lifecycle']==1 and status['checks']['pixel_twins']>1
at=r.locate();base=r.DUMP_BASE;b=(r.ROOT/'tmp/build/route-ram.bin').read_bytes();(case/'full-checks-memory.bin').write_bytes(b)
def read(addr,size):
 assert base<=addr and addr+size<=base+len(b)
 return b[addr-base:addr-base+size]
check(Path('tmp/game/RedBaron/data/sim').read_bytes(),status['sim'],read,[x for x in ranges() if x[2]==0])
result=dict(memory_base=base,mirror=read_checks(b),cache=status['checks'],mirror_hook_original=True,full_flight_exit=json.loads((case/'full-flight/census.json').read_text())['mission_ended'])
assert result['full_flight_exit']
(case/'full-proof.json').write_text(json.dumps(result,indent=2)+'\n');print('FULL CACHE-ONLY PROOF',result,flush=True)
