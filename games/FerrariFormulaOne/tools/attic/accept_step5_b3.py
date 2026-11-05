from pathlib import Path
import json,hashlib,subprocess,sys
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reports={}
for name in ('state','elapsed','replay','contact','profile'):
 p=r/f'manifest/step5-b3-{name}-validation.json';d=json.loads(p.read_text());assert d['status']=='passed',(p,d['status']);reports[name]=str(p.relative_to(repo))
fixtures={};audits={}
for profile in ('a1200','a1200-fast'):
 for variant in ('verify','control-lean','lean'):
  p=r/f'tmp/step5/{profile}-b3-v4-matrix-{variant}-fine';d=json.loads((p/'result.json').read_text());b=r/('tmp/build/step5-b3-native-control-lean-v4/fine.slave' if variant=='control-lean' else f'tmp/build/step5-b3-v4/{variant}/fine.slave');assert d['status']=='complete' and d['slave_sha256']==sha(b)
 for typ,n,build in (('recovery',1008,'step5-b3-recovery-v4'),('contact-counter',128,'step5-b3-v4-contact-counter')):
  p=r/f'tmp/step5/b3-v4-{typ}-{profile}/result.json';d=json.loads(p.read_text());assert d['status']=='passed' and d['cases']==n and d['slave_sha256']==sha(r/f'tmp/build/{build}/fine.slave');fixtures[typ+'-'+profile]=str(p.relative_to(repo))
 p=r/f'tmp/step5/{profile}-b3-v4-matched-b3';d=json.loads((p/'result.json').read_text());assert d['slave_sha256']==sha(r/'tmp/build/step5-b3-v4/lean/fine.slave');audit=json.loads((p/'schedule-audit.json').read_text());assert audit['passed'] and audit['pulse_updates']==4 and audit['updates']==20;audits[profile]=audit
source=repo/'Games/FerrariFormulaOne_WHD.s';release=r/'tmp/build/release/FerrariFormulaOne.slave'
assert sha(source)=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
assert sha(release)=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
assert b'FerrariFormulaOne_UpdateHooks.s' not in source.read_bytes()
expected={('verify',0):'8225d36a5faff1d4bc0faa08abb2e65d0785c367eecf491dd8b77dc84e7502be',('verify',1):'8931b21acb5b85fbfbf0671a799e4bbf0d150c64536e69fd8d607ecfbcc58a08',('verify',3):'0c6700789b6352d4894cfe8296427fd6933c947742b1b1fbf3bc28a158dd20b6',('lean',0):'f3685f62d92f381419f6f0db79f38a6a9c443d2673b1d069f778efdd356bea39',('lean',1):'07896f39f0467485eebd2d1521cd185b51ba0fd8bd3e0e60ecee28423b97dece',('lean',3):'82cd36f590b40bfb98a1c764741d2b9b793db882a4afd7cb3ec7542a004c7ba3'}
for (v,p),h in expected.items():assert sha(r/f'tmp/build/step5-s3/{v}-p{p}/fine.slave')==h
out={'status':'passed','scope':'B3 candidate opponent bypass. 020 + Fast is gating; chip-only 020 is diagnostic only. No ordinary release activation, full-renderer/FPS or coarse-path acceptance.','reports':reports,'fixtures':fixtures,'schedule_audits':audits,'source_hashes':{str(p.relative_to(repo)):sha(p) for p in (repo/'Games/FerrariFormulaOne_UpdateHooks.s',repo/'Games/FerrariFormulaOne_Opponents.s')},'build_hashes':{v:sha(r/f'tmp/build/step5-b3-v4/{v}/fine.slave') for v in ('verify','lean')},'ordinary_source_sha256':sha(source),'ordinary_release_sha256':sha(release),'default_off':True,'disabled_b3_s3_binaries_exact':True,'cycle_results':json.loads((r/'manifest/step5-b3-profile-validation.json').read_text())['profiles'],'guard_cost_note':'The plan\'s <=8-cycle TST estimate is not the measured elapsed instruction cost: the live car index remains in Chip memory. Actual bus-inclusive costs are recorded in schedule_audits; aggregate 200000/400000 gates are unchanged.'}
(r/'manifest/step5-b3-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('B3 passed all final candidate gates')
