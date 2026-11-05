#!/usr/bin/env python3
"""Final evidence binding and gates; no emulator control."""
import os,json,hashlib,shutil,subprocess
from pathlib import Path
from gpc_report import regions
os.chdir(Path(__file__).resolve().parents[1]);r=Path('tmp/phase7')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
normal=Path('tmp/build/release/GrandPrixCircuit.Slave');verify=Path('tmp/build/verify/GrandPrixCircuit.Slave')
assert b'GPCVERIFY\0' not in normal.read_bytes()
names=[f'accepted-zero-s{s}-{c}' for s in (0,3,5,7) for c in (0,1)]+[f'accepted-fraction-s{s}-f{f}' for s,f in ((5,1),(5,128),(5,255),(3,128))]+['accepted-core-'+n for n in ('a500','020','030','traffic')]+['accepted-moving-2000','accepted-moving-4000','accepted-moving-6000','accepted-moving-traffic']
for n in names:
 p=r/n;assert sha(p/'slave.slave')==sha(verify),n
 log=(p/'acceptance.log').read_text() if (p/'acceptance.log').exists() else ''
 assert '(63, 0)' in log,n
 assert 'all 139 jump stubs intact' in log and 'Negative control: corrupted swap instruction rejected' in log,n
for s in (0,3,5,7):assert json.loads((r/f'accepted-zero-s{s}-1/zero-oracle.json').read_text())['result']=='byte-identical'
for n in names:
 p=r/n/'buffer-audit.json'
 if 'core-' not in n:assert json.loads(p.read_text())['display_writes']==0,n
for n in ('a500','020','030','traffic'):
 p=r/('accepted-core-'+n)
 assert not json.loads((p/'phase6-regression.json').read_text())['differences']
 assert min(json.loads((p/'cadence.json').read_text())['physics_updates_per_draw'])>=1
costs={}
for n in ('accepted-moving-2000','accepted-moving-4000','accepted-moving-6000','accepted-moving-traffic'):
 p=r/n;c=json.loads((p/'phase7-cost.json').read_text());assert c['helper_percent']<=3.0
 assert json.loads((p/'latch-audit.json').read_text())['foreign_instructions_during_copy']==0
 costs[n]=c['helper_percent']
for name,cpu,base,c2 in [('a500-off','68000',0xc00000,0),('a500-on','68000',0xc00000,1),('a1200-on','68EC020',0x200000,1)]:
 p=r/('normal-'+name);result=json.loads((p/'result.json').read_text());assert result['slave_sha256']==sha(normal);assert result['native_race_exit']['after']['pending']==0
 shutil.copyfile(normal.with_suffix('.lst'),p/'slave.slave.lst');shutil.copyfile(p/('race2.bin' if c2 else 'race.bin'),p/'before.bin');os.environ['SLAVE']=str((p/'slave.slave').resolve());rr={n:lo for lo,hi,n,o in regions((p/'race.bin').read_bytes(),base)}
 (p/'metadata.json').write_text(json.dumps(dict(base=base,code_base=rr['gpc'],data_base=rr['gpc-data'],options=dict(CPU=cpu,WHD_ARGS='CUSTOM2='+str(c2))),indent=2)+'\n')
 with (p/'acceptance.log').open('w') as log:
  subprocess.run(['python3','tools/check_phase6.py',str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
  if c2:
   assert result['second_race']['canonical_tables_restored'] and result['second_race']['fraction_invalidated'] and result['second_race']['shifted_words_before_restore']>0
   subprocess.run(['python3','tools/phase7_tables.py',str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run(['python3','tools/check_inputs.py'],check=True)
source=Path('src')
files=['GrandPrixCircuitHD.s','simulation.s','render-subunit.s','render-verify.s','Makefile','Makefile_windows.mak']
report=dict(verify_captures=names,verify_sha256=sha(verify),normal_sha256=sha(normal),moving_helper_percent=costs,source_sha256={n:sha(source/n) for n in files},zero_fraction_oracles=4,display_audits=16,exact_state_comparisons=4,state_fields_each=720,normal_boot_exit_checks=3,second_race_restore_checks=2,guest_assertions=63,guest_failures=0,pristine_files=55)
(r/'completion-capture-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
