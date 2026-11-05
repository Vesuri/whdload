"""Single post-change spill check, after the serialized timing pairs."""
import os,sys,subprocess,time
from pathlib import Path
last=Path('tmp/completion-b1-060-on.log');batch=Path('tmp/completion-b1-rest.log')
while not last.exists() or 'CASE COMPLETE' not in last.read_text():
 if 'Traceback' in batch.read_text():raise SystemExit('Memory comparison failed; inspect owned case')
 time.sleep(1)
sys.path.insert(0,'tools');from completion_machines import environment
sys.path.insert(0,'tools');import route_status as r,step_log
env=environment('020',65536);env.update(VERIFY_ALLOC_LOG='1',BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
env['WHD_ARGS']=env['WHD_ARGS'].replace('CUSTOM5=0','CUSTOM5=8')
out='tmp/prof/completion-b1-post'
subprocess.run(['python3','-B','tools/reach_flight.py','--no-shot','--out',out],env=env,check=True)
print(step_log.advance(8),flush=True)
subprocess.run(['python3','-B','tools/collect_alloc.py',out],env=env,check=True)
subprocess.run(['python3','-B','tools/paint_log.py','--out',out+'/cache.json'],env=env,check=True)
print(r.command('quit'),flush=True)
