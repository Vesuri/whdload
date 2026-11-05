import os,sys,subprocess,re,json
from pathlib import Path
sys.path.insert(0,'tools');from completion_machines import environment
sys.path.insert(0,'tools');import route_status as r
env=environment('020',0x38000);env.update(BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
out=Path('tmp/prof/completion-c1-twin-r2')
subprocess.run([sys.executable,'-B','tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True)
symbols={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
state=r.read(r.locate());base=state['game_anchor']-symbols['tape_game_anchor']
result=r.command(f'gdb x/1uw {base+symbols["time_exp_result"]:#x}')
print(result,flush=True);assert re.search(r':\s+40960\b',result),result
(out/'twin.txt').write_text(result)
print(r.command('quit'),flush=True)
print('C1 TWIN COMPLETE',flush=True)
