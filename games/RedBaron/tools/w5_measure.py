import argparse,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('machine',choices=['a500','020','030']);p.add_argument('mask',type=int);p.add_argument('--suffix',default='');a=p.parse_args()
out=Path(f'tmp/prof/w5-{a.machine}-{a.mask}{a.suffix}')
def run(*cmd): subprocess.run([sys.executable,*map(str,cmd)],check=True)
run('tools/w5_boot.py',a.machine,a.mask,out)
import step_log
step_log.advance(8)
if a.machine=='030': run('tools/capture_current.py','--out',out/'dma','--fields',20)
else:
 for i,n in enumerate((100,100,50)): run('tools/capture_current.py','--out',out/f'chunk{i}','--fields',n)
if a.machine!='030':
 m=json.loads((out/'entry.json').read_text());run('tools/pacing_costs.py',*[out/f'chunk{i}/trace.bin' for i in range(3)],'--sim',m['entry']['sim'],'--out',out/'costs.json')
run('tools/w5_saved_audit.py',out)
run('tools/w4_rate.py',a.machine,out)
import route_status as r
r.command('shot '+str((out/'end.png').resolve()))
(out/'complete.json').write_text(json.dumps(dict(complete=True),indent=2)+'\n')
