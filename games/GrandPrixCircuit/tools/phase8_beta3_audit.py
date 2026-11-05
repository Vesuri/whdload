from pathlib import Path
import os,json,hashlib,subprocess,sys
from gpc_report import regions
root=Path(__file__).resolve().parents[1]
results={}
for name,cpu,base in [('a500-beta3','68000',0xc00000),('040-beta3','68040',0x880000)]:
 cap=root/'tmp/phase8'/('normal-'+name);result=json.loads((cap/'result.json').read_text());blob=(cap/'race.bin').read_bytes();os.environ['SLAVE']=str(cap/'slave.slave');rr={n:lo for lo,hi,n,o in regions(blob,base)}
 assert hashlib.sha256((cap/'slave.slave').read_bytes()).hexdigest()==result['slave_sha256']
 (cap/'before.bin').write_bytes(blob)
 (cap/'metadata.json').write_text(json.dumps(dict(base=base,code_base=rr['gpc'],data_base=rr['gpc-data'],options={'CPU':cpu,'WHD_ARGS':'CUSTOM2=1'}),indent=2)+'\n')
 with (cap/'code-audit.txt').open('w') as log:
  subprocess.run([sys.executable,str(root/'tools/check_phase6.py'),str(cap)],stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run([sys.executable,str(root/'tools/phase7_tables.py'),str(cap)],stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run([sys.executable,str(root/'tools/check_music.py'),str(cap/'intro.bin'),'--base',hex(base),'--candidate'],stdout=log,stderr=subprocess.STDOUT,check=True)
 if cpu=='68040':
  conf=(cap/'debug.uae').read_text();log=(cap/'mmu-log.txt').read_text()
  assert 'cpu_model=68040' in conf and 'mmu_model=68040' in conf and 'cachesize=0' in conf
  assert 'TC=8000 enabled=1' in log and 'MMU=68040, JIT=0' in log
 result['exact_code_and_table_audits']=True;result['mmu_translation_verified']=cpu=='68040';results[name]=result
 print(name,'PASS',flush=True)
(root/'tmp/phase8/beta3-normal-audit.json').write_text(json.dumps(results,indent=2)+'\n')
