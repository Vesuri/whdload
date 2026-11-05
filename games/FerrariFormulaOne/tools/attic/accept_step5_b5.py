from pathlib import Path
import json,hashlib,re
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reports={}
for name in ('v5-state','v5-elapsed','v5-replay','profile','hook','disabled'):
 p=r/f'manifest/step5-b5-{name}-validation.json';d=json.loads(p.read_text());assert d['status']=='passed',(p,d['status']);reports[name]=str(p.relative_to(repo))
fixtures={}
for name,build,count in [('sqrt64','sqrt64',408),('seed','seed',1942),('speed-feedback','speed-feedback',1003),('speed-rate','speed-rate',130),('speed-extended','speed-extended',1264),('velocity-scale','velocity',9090),('velocity-apply','velocity-apply',56),('velocity-carry','velocity-carry',3216),('wear-extended','wear-extended',4244),('wide-extended','wide-extended',2383)]:
 p=r/f'tmp/step5/b5v5-{name}-a1200/result.json';d=json.loads(p.read_text());variant='b00' if name=='wide-extended' else 'fine'
 assert d['status']=='passed' and len(d['cases'])==count,(name,d['status'],len(d['cases']))
 assert d['slave_sha256']==sha(r/f'tmp/build/step5-b5v5-{build}-test/{variant}.slave'),name
 fixtures[name]=dict(cases=count,result=str(p.relative_to(repo)),slave_sha256=d['slave_sha256'])
audits={}
for profile in ('a1200','a1200-fast'):
 for variant in ('verify','lean'):
  p=r/f'tmp/step5/{profile}-b5-v5-matrix-{variant}-fine';d=json.loads((p/'result.json').read_text());assert d['status']=='complete' and d['slave_sha256']==sha(r/f'tmp/build/step5-b5-v5-compact/{variant}/fine.slave')
  if variant=='verify':assert d['scalar_trace_capacity']==4000 and d['probe']['speed_records_count']==200
 p=r/f'tmp/step5/{profile}-b5-v5-matched-b5/schedule-audit.json';d=json.loads(p.read_text());assert d['passed'] and d['updates']==20 and d['pulse_updates']==4;audits[profile]=d
assert (r/'tmp/build/step5-b5-v5-compact/lean/fine.slave').read_bytes()==(r/'tmp/build/step5-b5-v5/lean/fine.slave').read_bytes()
source=repo/'Games/FerrariFormulaOne_WHD.s';release=r/'tmp/build/release/FerrariFormulaOne.slave'
assert sha(source)=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761';assert sha(release)=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
assert b'FerrariFormulaOne_UpdateHooks.s' not in source.read_bytes()
s=(repo/'Games/FerrariFormulaOne_Sqrt.s').read_text().split('FF1RootSeeds:',1)[1].split('        else',1)[0];entries=[int(v,16) for v in re.findall(r'\$([0-9a-f]{4})',s)]
import math
assert entries==[math.isqrt(k<<22) for k in range(1024)]
models={}
for name in ('step5-b5-seed-validation.json','step5-b5v2-u32-model.json'):
 p=r/'manifest'/name;d=json.loads(p.read_text());assert d['status']=='passed';models[name]=d
out=dict(status='passed',scope='B5 default-off 020 conversion-helper tuning. Fast gates the phase; chip-only adapted mode is diagnostic. No coarse path, ordinary release or rendered FPS activation.',reports=reports,fixtures=fixtures,schedule_audits=audits,models=models,source_hashes={str(p.relative_to(repo)):sha(p) for p in [repo/f'Games/FerrariFormulaOne_{x}.s' for x in ('Sqrt','Speed','Velocity','Wear','UpdateHooks')]},build_hashes={v:sha(r/f'tmp/build/step5-b5-v5-compact/{v}/fine.slave') for v in ('verify','lean')},ordinary_source_sha256=sha(source),ordinary_release_sha256=sha(release),default_off=True,disabled_b5_b4_binaries_exact=True,cycle_results=json.loads((r/'manifest/step5-b5-profile-validation.json').read_text())['profiles'],gate_note='Fast player conv_helper mean 4968.0 <= 5000, a narrow 32-cycle margin in the prescribed 20-update window. Whole-update peak is 341092; B6 peak/debt and B8 rendering acceptance remain outstanding.',trace_fixture=dict(default_scalar_records=4096,compact_scalar_records=4000,used_scalar_records=200,overflow_guard_matches_allocation=True,ordinary_abi_unchanged=True,reason='Uncompacted VERIFY failed WHDLoad DOS error 103 loading the slave on chip-only 020; compact VERIFY is 779640 bytes and preserves all 101 state checkpoints and replay checks.',diagnostic='tmp/dev/tmp/step5/b5-verify-startup/whd-output.txt'))
(r/'manifest/step5-b5-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('B5 passed all candidate gates')
