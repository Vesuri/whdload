from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear_display_transition','address':'0x6bf84','bytes':4}]
report={'scope':'Native-step demo per-car position bridge; not adapted physics or reset/contact acceptance','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/(profile+'-position-bridge-v2-'+v) for v in ('control','bridge')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d['status']=='complete' for d in results):continue
 mismatches={}
 for tick in (125,150,175,225):
  data=[(p/f'loop{tick}.bin').read_bytes() for p in paths]
  mismatches[tick]=[b['name'] for b in blocks if data[0][int(b['address'],16):int(b['address'],16)+b['bytes']]!=data[1][int(b['address'],16):int(b['address'],16)+b['bytes']]]
 row={'exact':not any(mismatches.values()),'mismatches':mismatches,'probe':results[1]['probe'],'shadow_matches_all_cars':results[1]['shadow_matches_all_cars']}
 report['profiles'][profile]=row
 print(profile,json.dumps(row))
 assert row['exact'] and row['shadow_matches_all_cars']
report['status']='passed' if len(report['profiles'])==2 else 'incomplete'
report['source_sha256']=hashlib.sha256((r.parent.parent/'Games/FerrariFormulaOne_Position.s').read_bytes()).hexdigest()
(r/'manifest/step5-position-bridge-v2-validation.json').write_text(json.dumps(report,indent=2)+'\n')
