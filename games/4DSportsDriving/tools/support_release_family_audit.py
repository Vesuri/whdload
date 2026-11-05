#!/usr/bin/env python3
"""Partial offline body checks against unchanged original and phase-family bands."""
import json,hashlib,collections
from pathlib import Path
root=Path('tmp/prof');criteria=json.loads((root/'natural-crest-criteria.json').read_text());family_path=root/'native-contact-phase-criteria.json'
assert hashlib.sha256(family_path.read_bytes()).hexdigest()=='74afe3d039870269ccf4d160434ec52f05fe195dfb8dc6c338a3aeca613d64ce'
family=json.loads(family_path.read_text());reports=[]
for label,cap in [('nominal','contact-prediction-d9-long'),('minus64','contact-prediction-d9-minus64-long'),('plus64','contact-prediction-d9-plus64-long')]:
    path=root/cap/'support-release-comparison.json';data=json.loads(path.read_text());rows=data['records'];ix={r['tick']:r for r in rows};checks=[]
    for t,bands in family['common_bands'].items():
        tick=int(t)*5
        if tick not in ix:continue
        r=ix[tick];values=dict(zip(('x','y','z'),r['position']));values['pitch']=r['pitch']
        for key,val in values.items():
            band=bands[key];checks.append(dict(tick=tick,field=key,actual=val,**band,passed=band['low']<=val<=band['high']))
    failed=[c for c in checks if not c['passed']]
    metrics=dict(peak_height=max(r['position'][1] for r in rows),minimum_pitch=min(r['pitch'] for r in rows),maximum_pitch=max(r['pitch'] for r in rows),final_y=rows[-1]['position'][1],final_z=rows[-1]['position'][2],final_pitch=rows[-1]['pitch'])
    original={k:dict(actual=v,reference=criteria['native20']['metrics'][k],limit=criteria['limits'][k],passed=abs(v-criteria['native20']['metrics'][k])<=criteria['limits'][k]) for k,v in metrics.items()} if label=='nominal' else None
    reports.append(dict(phase=label,canonical_steps_exact=data['canonical_steps_exact'],checks=len(checks),failed_counts=dict(collections.Counter(c['field'] for c in failed)),failures=failed,paired_maxima=data['maxima'],nominal_original_metric_checks=original))
out=dict(cases=reports,criteria_sha256=hashlib.sha256(family_path.read_bytes()).hexdigest(),scope='Reject-only offline diagnostic. Initial phase state from respective live anchor, then recurrent pose/contact. Distances/roof/impact externally prescribed, no feedback into drivetrain. Checks only XYZ/pitch at 70 common boundaries9.1..16s, not full vehicle or flight outcome acceptance. Original criteria unchanged.')
(root/'support-release-family-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k not in ('failures','paired_maxima')} for r in reports],indent=2))
