import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0,'tools')
from completion_machines import environment
sys.path.insert(0,'tools')
import route_status as r, step_log
out=Path('tmp/prof/artwork-sparse-twin-060-4')
if out.exists():raise SystemExit('Refusing overwrite')
pid=Path('tmp/run/default/.run/fsuae.pid')
if pid.exists():
 p=subprocess.run(['ps','-p',pid.read_text().strip(),'-o','stat=,command='],capture_output=True,text=True)
 if p.returncode==0 and not p.stdout.lstrip().startswith('Z'):raise SystemExit('Existing process: '+p.stdout)
env=environment('060',0xb0ffa)
env.update(BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
subprocess.run([sys.executable,'-B','tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True)
symbols={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
state=r.read(r.locate());base=state['game_anchor']-symbols['tape_game_anchor']
print(step_log.advance(20),flush=True)
for name,size in [('artwork_cache_twin_result',16),('artwork_cache_stats',12)]:
 address=base+symbols[name];path=out/(name+'.bin')
 print(r.command(f'gdb dump binary memory {path} {address:#x} {address+size:#x}'),flush=True)
 print(name,path.read_bytes().hex(),flush=True)
result=(out/'artwork_cache_twin_result.bin').read_bytes()
assert int.from_bytes(result[:4],'big')==63,result.hex()
assert int.from_bytes(result[12:16],'big')==6,result.hex()
(out/'result.json').write_text(json.dumps(dict(front_programs=[2,3,4],pixel_bytes_per_case=40000,drawing_state_bytes=24,passed=True)))
print(r.command('shot '+str((out/'final.png').resolve())),flush=True)
print(r.command('quit'),flush=True)
print('SPARSE ARTWORK PIXEL TWIN PASSED',flush=True)
