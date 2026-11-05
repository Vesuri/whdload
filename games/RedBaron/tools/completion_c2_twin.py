import os,sys,subprocess,re,json
from pathlib import Path
sys.path.insert(0,'tools');from completion_machines import environment
sys.path.insert(0,'tools');import route_status as r,step_log
env=environment('020',0x70000);env.update(VERIFY_BANK_CYCLE='1',BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
out=Path('tmp/prof/completion-c2-twin-r2')
subprocess.run([sys.executable,'-B','tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True)
symbols={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
state=r.read(r.locate());base=state['game_anchor']-symbols['tape_game_anchor'];header=base+symbols['model_bank_header']
def snap(name):
 p=out/(name+'.bin');print(r.command(f'gdb dump binary memory {p} {header:#x} {header+44:#x}'),flush=True)
snap('entry');print(step_log.advance(8),flush=True);snap('bank-change')
print(r.command(f'until {state["sim"]+0x21f60:#x}'),flush=True);snap('exit')
print(r.command('shot '+str(out/'exit.png')),flush=True)
print('C2 TWIN EXIT REACHED; PAUSED',flush=True)
