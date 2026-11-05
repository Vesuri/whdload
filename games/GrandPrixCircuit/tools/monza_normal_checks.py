import os,subprocess,json,hashlib
from pathlib import Path
from gpc_report import regions
root=Path(__file__).resolve().parents[1];os.chdir(root);results={}
for name,opts in [('a500-beta4',dict(CPU='68000',AMIGA_MODEL='A500',CHIP_KB='512',FAST_KB='0',SLOW_KB='1536')),('030-beta4',dict(CPU='68030',AMIGA_MODEL='A1200',AMIGA_SETUP='a1200-030',CHIP_KB='2048',FAST_KB='8192',SLOW_KB='0')),('040-beta4',dict(CPU='68040',AMIGA_MODEL='A1200',AMIGA_SETUP='a1200-040',CHIP_KB='2048',FAST_KB='8192',SLOW_KB='0'))]:
 cap=root/'tmp/phase8'/('normal-'+name);cap.mkdir(exist_ok=True)
 env=dict(os.environ,OUT_ROOT='tmp/phase8',CELL=name,SECOND_RACE='1',CUSTOM2_VALUE='1',SLAVE=str(root/'tmp/build/release/GrandPrixCircuit.Slave'),WARP='1',DETERMINISTIC='1',JOY0='none',JOY1='none',WHD_ARGS='CUSTOM2=1'+(' MMU' if opts['CPU']!='68000' else ''),**opts)
 print('START',name,flush=True)
 with (cap/'run.log').open('w') as log:subprocess.run(['python3','tools/phase8_lifecycle.py'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 base=0xc00000 if opts['CPU']=='68000' else 0x880000
 blob=(cap/'race.bin').read_bytes();os.environ['SLAVE']=str(cap/'slave.slave');rr={n:lo for lo,hi,n,o in regions(blob,base)}
 (cap/'before.bin').write_bytes(blob);(cap/'metadata.json').write_text(json.dumps(dict(base=base,code_base=rr['gpc'],data_base=rr['gpc-data'],options={k:env[k] for k in ('CPU','WHD_ARGS')}),indent=2)+'\n')
 with (cap/'code-audit.txt').open('w') as log:
  for args in [['check_phase6.py',str(cap)],['phase7_tables.py',str(cap)],['check_music.py',str(cap/'intro.bin'),'--base',hex(base),'--candidate']]:
   subprocess.run(['python3','tools/'+args[0],*args[1:]],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 result=json.loads((cap/'result.json').read_text());assert result['slave_sha256']==hashlib.sha256((root/'tmp/build/release/GrandPrixCircuit.Slave').read_bytes()).hexdigest()
 result['code_tables_music_audits']=True;results[name]=result
 (root/'tmp/phase8/beta4-normal-audit.json').write_text(json.dumps(results,indent=2)+'\n')
 print('PASS',name,flush=True)
