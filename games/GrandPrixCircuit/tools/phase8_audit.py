#!/usr/bin/env python3
"""Audit completed normal compatibility captures with existing strict code/table checkers."""
from pathlib import Path
import json,os,shutil,subprocess,sys
from gpc_report import regions
root=Path(__file__).resolve().parents[1]
report=root/'tmp/phase8/compatibility-audit.json'
results=json.loads(report.read_text()) if report.exists() else {}
for cap in sorted((root/'tmp/phase8').glob('normal-*')):
 if not (cap/'result.json').exists() or cap.name in results:continue
 result=json.loads((cap/'result.json').read_text());blob=(cap/'race.bin').read_bytes()
 base=0xc00000 if cap.name.startswith('normal-a500') else 0xa00000-len(blob)
 os.environ['SLAVE']=str(cap/'slave.slave');rr={n:lo for lo,hi,n,o in regions(blob,base)}
 cpu='68000' if base==0xc00000 else '68040';c2=result['custom2']
 shutil.copyfile(root/'tmp/build/release/GrandPrixCircuit.lst',cap/'slave.slave.lst')
 (cap/'before.bin').write_bytes(blob)
 (cap/'metadata.json').write_text(json.dumps(dict(base=base,code_base=rr['gpc'],data_base=rr['gpc-data'],options={'CPU':cpu,'WHD_ARGS':f'CUSTOM2={c2}'}),indent=2)+'\n')
 with (cap/'code-audit.txt').open('w') as f:subprocess.run([sys.executable,str(root/'tools/check_phase6.py'),str(cap)],check=True,stdout=f,stderr=subprocess.STDOUT)
 if c2:
  with (cap/'table-audit.txt').open('w') as f:subprocess.run([sys.executable,str(root/'tools/phase7_tables.py'),str(cap)],check=True,stdout=f,stderr=subprocess.STDOUT)
 if cpu=='68040':
  conf=(cap/'debug.uae').read_text();log=(cap/'mmu-log.txt').read_text()
  assert 'cpu_model=68040' in conf and 'mmu_model=68040' in conf and 'cachesize=0' in conf
  assert 'TC=8000 enabled=1' in log and 'MMU=68040, JIT=0' in log
 result['exact_code_audit']=True;result['mmu_translation_verified']=cpu=='68040';results[cap.name]=result
 print(cap.name,'PASS',flush=True)
(root/'tmp/phase8/compatibility-audit.json').write_text(json.dumps(results,indent=2)+'\n')
