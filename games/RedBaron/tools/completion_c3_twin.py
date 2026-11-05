import os,sys,subprocess,re,json
from pathlib import Path
sys.path.insert(0,'tools');from completion_machines import environment
from face_model import check_header
sys.path.insert(0,'tools');import route_status as r,step_log
env=environment('a500',0x31fff);env.update(CHIP_KB='1024',FAST_KB='2048',BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
env['EXTRA_ARGS']=env['EXTRA_ARGS'].replace('--slow_memory=1536','--slow_memory=0')
out=Path('tmp/prof/completion-c3-twin')
subprocess.run([sys.executable,'-B','tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True)
symbols={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
state=r.read(r.locate());base=state['game_anchor']-symbols['tape_game_anchor'];header=base+symbols['face_verify_header']
print(step_log.advance(8),flush=True)
p=out/'twin.bin';print(r.command(f'gdb dump binary memory {p} {header:#x} {header+32:#x}'),flush=True)
print('C3 TWIN PASSED',check_header(p.read_bytes()),flush=True)
print(r.command('quit'),flush=True)
