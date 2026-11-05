#!/usr/bin/env python3
import os,time,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
while True:
 try:os.kill(3004,0)
 except ProcessLookupError:break
 time.sleep(5)
share=Path.home()/'.local/share/amiga'
runtimes={'17.2':root/'tmp/phase8/whd172/WHDLoad/C/WHDLoad','19.2':share/'WHDLoad/C/WHDLoad','20.0':share/'WHDLoad/C/WHDLoad','20.1':root/'tmp/phase8/whd201/WHDLoad/C/WHDLoad'}
results={}
for version,model,c2 in [('17.2','a500',0),('17.2','a500',1),('17.2','040',0),('17.2','040',1),('19.2','040',0),('19.2','040',1),('20.0','040',0),('20.1','040',0),('20.1','040',1)]:
 name=f'{model}-{version}-{c2}';out=root/'tmp/phase8'/('normal-'+name);out.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,OUT_ROOT='tmp/phase8',CELL=name,SECOND_RACE=str(c2),CUSTOM2_VALUE=str(c2),SLAVE=str(root/'tmp/build/release/GrandPrixCircuit.Slave'),WHDLOAD_BINARY=str(runtimes[version]),WARP='1',DETERMINISTIC='1',JOY0='none',JOY1='none',WHD_ARGS=f'CUSTOM2={c2}'+(' MMU' if model=='040' else ''))
 if model=='040':env.update(AMIGA_SETUP='a1200-040',AMIGA_MODEL='A1200',CPU='68040',CHIP_KB='2048',FAST_KB='8192',SLOW_KB='0')
 else:env.update(AMIGA_MODEL='A500',CPU='68000',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536')
 print('START',name,flush=True)
 with (out/'run.log').open('w') as log:
  code=subprocess.run(['python3','tools/phase8_lifecycle.py'],env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 results[name]=code;(root/'tmp/phase8/matrix.json').write_text(json.dumps(results,indent=2)+'\n');print('END',name,code,flush=True)
 if code:break
