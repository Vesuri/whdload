import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0,'tools')
from completion_machines import environment
sys.path.insert(0,'tools')
import route_status as r, step_log
out=Path('tmp/prof/completion-e2-gauge-twin-r4')
if out.exists():raise SystemExit('Refusing overwrite')
pid=Path('tmp/run/default/.run/fsuae.pid')
if pid.exists():
 p=subprocess.run(['ps','-p',pid.read_text().strip(),'-o','stat=,command='],capture_output=True,text=True)
 if p.returncode==0 and not p.stdout.lstrip().startswith('Z'):raise SystemExit('Existing process: '+p.stdout)
env=environment('060',0x72ffa)
env.update(BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
subprocess.run([sys.executable,'-B','tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True)
symbols={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
state=r.read(r.locate());base=state['game_anchor']-symbols['tape_game_anchor']
address=base+symbols['instrument_cache_twin_result']; header=out/'early-header.bin'
print(r.command(f'gdb dump binary memory {header} {address:#x} {address+32:#x}'),flush=True)
if not int.from_bytes(header.read_bytes()[16:20],'big'):
 print(step_log.advance(80),flush=True)
for name,size in [('instrument_cache_twin_result',32),('instrument_cache_stats',8)]:
 address=base+symbols[name];path=out/(name+'.bin')
 print(r.command(f'gdb dump binary memory {path} {address:#x} {address+size:#x}'),flush=True)
 print(name,path.read_bytes().hex(),flush=True)
head=(out/'instrument_cache_twin_result.bin').read_bytes()
scratch=int.from_bytes(head[8:12],'big')
if scratch:
 path=out/'twin-state-pair.bin'
 print(r.command(f'gdb dump binary memory {path} {scratch+40000:#x} {scratch+40080:#x}'),flush=True)
 address=base+symbols['instrument_cache_twin_post'];path=out/'twin-state-actual.bin'
 print(r.command(f'gdb dump binary memory {path} {address:#x} {address+40:#x}'),flush=True)
print(r.command('shot '+str((out/'final.png').resolve())),flush=True)
print(r.command('quit'),flush=True)
from instrument_cache_result import check
result=check((out/'instrument_cache_twin_result.bin').read_bytes(),
             (out/'instrument_cache_stats.bin').read_bytes())
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print('E2 GAUGE PIXEL TWIN PASSED',result,flush=True)
