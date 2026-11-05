from pathlib import Path
import json,hashlib,re
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reports={}
for key,name in [('state','v4-state'),('elapsed','v4-elapsed'),('replay','v4-replay'),('contact','contact'),('profile','profile'),('hooks','hook'),('disabled','disabled')]:
 p=r/f'manifest/step5-b4-{name}-validation.json';d=json.loads(p.read_text());assert d['status']=='passed',(p,d['status']);reports[key]=str(p.relative_to(repo))
fixtures={};audits={}
for profile in ('a1200','a1200-fast'):
 for variant in ('verify','lean'):
  p=r/f'tmp/step5/{profile}-b4-v4-matrix-{variant}-fine';d=json.loads((p/'result.json').read_text());assert d['status']=='complete' and d['slave_sha256']==sha(r/f'tmp/build/step5-b4-v4/{variant}/fine.slave')
 for typ,n,build in [('recovery',1008,'step5-b4-recovery-v4'),('contact-counter',128,'step5-b4-v4-contact-counter')]:
  p=r/f'tmp/step5/b4-v4-{typ}-{profile}/result.json';d=json.loads(p.read_text());assert d['status']=='passed' and d['cases']==n and d['slave_sha256']==sha(r/f'tmp/build/{build}/fine.slave');fixtures[typ+'-'+profile]=str(p.relative_to(repo))
 p=r/f'tmp/step5/{profile}-b4-v4-matched-b4-retry1/schedule-audit.json';d=json.loads(p.read_text());assert d['passed'] and d['updates']==20 and d['pulse_updates']==4;audits[profile]=d
for typ,n in [('wear',254),('steering',80)]:
 p=r/f'tmp/step5/b4-{typ}-a1200/result.json';d=json.loads(p.read_text());assert d['status']=='passed' and len(d['cases'])==n and d['slave_sha256']==sha(r/f'tmp/build/step5-b4-{typ}-test/fine.slave');fixtures[typ]=str(p.relative_to(repo))
source=repo/'Games/FerrariFormulaOne_WHD.s';release=r/'tmp/build/release/FerrariFormulaOne.slave'
assert sha(source)=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761';assert sha(release)=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f';assert b'FerrariFormulaOne_UpdateHooks.s' not in source.read_bytes()
for variant in ('verify','lean'):assert (r/f'tmp/build/step5-b4-refactor/{variant}/fine.slave').read_bytes()==(r/f'tmp/build/step5-b4-v4/{variant}/fine.slave').read_bytes()
listing=(r/'tmp/build/step5-b4-v4/lean/fine.list').read_text();sym={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',listing,re.M)};assert sym['player_state_end']-sym['player_state']==64
out=dict(status='passed',scope='B4 default-off mode-8 player hook consolidation. Fast is gating; chip-only run is diagnostic. No ordinary/coarse/FPS activation or acceptance.',reports=reports,fixtures=fixtures,schedule_audits=audits,source_hashes={str(p.relative_to(repo)):sha(p) for p in [repo/f'Games/FerrariFormulaOne_{x}.s' for x in ('UpdateHooks','Steering','Wear')]},build_hashes={v:sha(r/f'tmp/build/step5-b4-v4/{v}/fine.slave') for v in ('verify','lean')},ordinary_source_sha256=sha(source),ordinary_release_sha256=sha(release),default_off=True,disabled_b4_b3_binaries_exact=True,macro_refactor_bytes_exact=True,player_state_bytes=64,cycle_results=json.loads((r/'manifest/step5-b4-profile-validation.json').read_text())['profiles'],gate_note='Fast player mean 49977.0, only 23 cycles below 50000 in the measured 20-update window. This is a narrow measured pass, not broad capacity headroom.',trace_storage='tmp/dev/tmp/step5/b4-trace-storage.json')
(r/'manifest/step5-b4-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('B4 passed all candidate gates')
