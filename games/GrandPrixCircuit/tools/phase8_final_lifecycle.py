import os,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
for name,opts in [('a500-beta2',dict(CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536',INTRO_TRACE='100')),('040-beta2',dict(CPU='68040',AMIGA_MODEL='A1200',AMIGA_SETUP='a1200-040',CHIP_KB='2048',FAST_KB='8192',SLOW_KB='0'))]:
 cap=Path('tmp/phase8/normal-'+name);cap.mkdir(exist_ok=True)
 env=dict(os.environ,OUT_ROOT='tmp/phase8',CELL=name,SECOND_RACE='1',CUSTOM2_VALUE='1',SLAVE=str(root/'tmp/build/release/GrandPrixCircuit.Slave'),WARP='1',DETERMINISTIC='1',JOY0='none',JOY1='none',WHD_ARGS='CUSTOM2=1'+(' MMU' if name.startswith('040') else ''),**opts)
 print('START',name,flush=True)
 with (cap/'run.log').open('w') as log:subprocess.run(['python3','tools/phase8_lifecycle.py'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (cap/'music-audit.txt').open('w') as log:subprocess.run(['python3','tools/check_music.py',str(cap/'intro.bin'),'--base','0xc00000' if name.startswith('a500') else '0x880000','--beta2'],stdout=log,stderr=subprocess.STDOUT,check=True)
 print('PASS',name,flush=True)

# Same-period deterministic 020 regression against the already accepted Phase 7.
old=Path('tmp/phase7/accepted-core-020');m=json.loads((old/'metadata.json').read_text());cap=Path('tmp/phase8/beta2-core-020');cap.mkdir(exist_ok=True)
env=dict(os.environ,**{k:v for k,v in m['options'].items() if v is not None});env.pop('BOOT_HUNK',None);env.update(PHASE3_FIELDS='720',SKIP_FIELDS='0',LATCH_AUDIT='1')
print('START core',flush=True)
with (cap/'run.log').open('w') as log:subprocess.run(['bash','tools/fixed_window.sh',str(cap)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
with (cap/'audit.log').open('w') as log:
 for cmd in [['tools/phase6_units.py',str(cap),str(cap/'slave.slave.lst')],['tools/check_phase6.py',str(cap)],['tools/phase7_tables.py',str(cap)],['tools/phase6_compare.py',str(old),str(cap),'--output',str(cap/'regression.json'),'--assert-core']]:
  subprocess.run(['python3',*cmd],stdout=log,stderr=subprocess.STDOUT,check=True)
print('PASS core',flush=True)
