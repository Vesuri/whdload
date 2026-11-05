#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys,hashlib
root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(root/'tools/phase8_audit.py')],check=True)
r=root/'tmp/phase8';m=json.loads((r/'matrix.json').read_text());assert len(m)==9 and set(m.values())=={0},m
checks=json.loads((r/'compatibility-audit.json').read_text());assert len(checks)==10
expected='e0765e5035febd4a9a928b440a966d2742c987528b0d7221ec256390f7aeec81'
for name,v in checks.items():
 assert v['slave_sha256']==expected and v['exact_code_audit']
 if '040' in name:assert v['mmu_translation_verified']
 assert v['native_race_exit']['after']['pending']==0
for n in ['normal-040-20-on','normal-040-19.2-1','normal-a500-17.2-1']:
 assert checks[n]['second_race']['canonical_tables_restored'] and checks[n]['second_race']['swaps']==40
subprocess.run([sys.executable,str(root/'tools/check_inputs.py')],check=True)
report={'normal_slave_sha256':expected,'compatibility_captures':checks,'runtimes':json.loads((r/'runtime-manifest.json').read_text()),'physical_hardware':'pending owner test; A1200/68040 40 MHz/MMU/32 MB/WHDLoad 19.x','pristine_files':55,'shared_lessons_commit':'39978a5'}
(r/'completion.json').write_text(json.dumps(report,indent=2)+'\n');print('10 normal-build compatibility captures PASS; physical test still pending')
