from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1]
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear_display_transition','address':'0x6bf84','bytes':4}]
report={'scope':'S2 VERIFY/lean, common startup RNG control; no-input demo, CUSTOM1=1 CUSTOM2=1, drawing omitted. Same first complete updates from loop 132 in each 48-field trace; startup in warp, measurement unwarped. All-car diagnostic, not Plan B or coarse acceptance.','profiles':{}}
for p,gate in (('a1200',588000),('a1200-fast',493000)):
 dirs=[r/'tmp/step5'/(p+'-verify-split-profile-'+v) for v in ('verify','lean')]
 data=[(d/'start.bin').read_bytes() for d in dirs]
 diffs=[x['name'] for x in blocks if data[0][int(x['address'],16):int(x['address'],16)+x['bytes']]!=data[1][int(x['address'],16):int(x['address'],16)+x['bytes']]]
 prof=[json.loads((d/'profile.json').read_text()) for d in dirs]
 pc=[json.loads((d/'percar.json').read_text()) for d in dirs]
 assert prof[0]['complete_updates']==prof[1]['complete_updates']
 assert all(a['per_update_cycles']==b['per_update_totals'] for a,b in zip(prof,pc))
 classified=[json.loads((d/'classified.json').read_text()) for d in dirs]
 assert all(abs(sum(c['totals'].values())-a['mean_cycles'])<0.001 for c,a in zip(classified,prof))
 v,l=[x['mean_cycles'] for x in prof]
 row={'passed':not diffs and l<=gate,'start_state_mismatches':diffs,'matched_complete_updates':prof[0]['complete_updates'],'verify_cycles':v,'lean_cycles':l,'saving_cycles':v-l,'saving_percent':100*(v-l)/v,'verify_ms':v/14187.58,'lean_ms':l/14187.58,'gate_cycles':gate,'gate_margin_cycles':gate-l,'verify_classes':pc[0]['totals'],'lean_classes':pc[1]['totals'],'verify_segments':pc[0]['segments'],'lean_segments':pc[1]['segments'],'lean_trace_cycles':pc[1]['totals'].get('trace',0)}
 report['profiles'][p]=row;print(p,{k:v for k,v in row.items() if not k.endswith(('classes','segments'))})
report['status']='passed' if all(x['passed'] for x in report['profiles'].values()) else 'failed'
(r/'manifest/step5-s2-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['status']=='passed'
