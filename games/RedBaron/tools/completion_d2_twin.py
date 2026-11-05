import sys,subprocess,re,json
from pathlib import Path
sys.path.insert(0,'tools');from completion_machines import environment
from game_time_debt import check_quantum_twin
sys.path.insert(0,'tools');import route_status as r,step_log
env=environment('a500',0x33fff);env.update(CHIP_KB='1024',FAST_KB='2048',VERIFY_WORLD_QUANTUM_TWIN='1',BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
env['EXTRA_ARGS']=env['EXTRA_ARGS'].replace('--slow_memory=1536','--slow_memory=0')
env['WHD_ARGS']='CUSTOM2=212991 CUSTOM5=-2146434560'
out=Path('tmp/prof/completion-d2-twin-r2')
subprocess.run([sys.executable,'-B','tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True)
symbols={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
state=r.read(r.locate());base=state['game_anchor']-symbols['tape_game_anchor']
print(step_log.advance(20),flush=True)
for label,size in [('time_quantum_header',28),('time_debt_header',32),('time_core_result',4)]:
 at=base+symbols[label];p=out/(label+'.bin');print(r.command(f'gdb dump binary memory {p} {at:#x} {at+size:#x}'),flush=True)
print('D2 TWIN PASSED',check_quantum_twin((out/'time_quantum_header.bin').read_bytes()),flush=True)
print('CORE CASES',int.from_bytes((out/'time_core_result.bin').read_bytes(),'big'),flush=True)
(out/'steps.json').write_text(json.dumps(step_log.collect(),indent=2)+'\n')
print(r.command('quit'),flush=True)
