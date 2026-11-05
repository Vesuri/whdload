import os,sys,json,shutil
from pathlib import Path
from capture_demo import ROOT,command,sha
from capture_session import Session
os.chdir(ROOT);previous=ROOT/'tmp/prof/s6-flow-direct-020';game=ROOT/'tmp/game/s6-reload-game';assert not game.exists()
shutil.copytree(ROOT/'tmp/game/HardDrivin_v3.0_0126/HardDrivin',game)
shutil.copyfile(previous/'hiscore-saved.bin',game/'data/hiscore.dat')
out=ROOT/'tmp/prof/s6-score-reload';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s6f-b.slave',out/'slave.slave')
s=Session(out,'a1200-020',out/'slave.slave',0x86dc);s.env['GAME_DIR']=game.name;s.env['WHD_ARGS']+=' CUSTOM1=1';s.env['SWAP_ONLY']='1'
try:
 s.boot();a=s.layout['a4']-0x64de;command(f'gdb dump binary memory {out.relative_to(ROOT)}/reloaded.bin {a:#x} {a+380:#x}')
 assert (out/'reloaded.bin').read_bytes()==(previous/'hiscore-plain.bin').read_bytes()
 r=dict(passed=True,bytes=380,sha256=sha(out/'reloaded.bin'));(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
finally:s.close()
