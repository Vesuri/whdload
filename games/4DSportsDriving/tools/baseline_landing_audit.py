#!/usr/bin/env python3
"""Cross-check baseline landing attribution against independent full-course poses."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tmp/prof'
inputs={20:('crest-landing20','natural-crest20'),50:('baseline-landing50','contact-return-crest-fast')}
report={}
paths={}
for hz,(motion_name,bridge_name) in inputs.items():
    cap=P/motion_name
    motion=json.loads((cap/'landing-motion-check.json').read_text())
    bridge=json.loads((P/bridge_name/'bridge.json').read_text())
    assert motion['rate']==bridge['rate']==hz
    bytick={r['tick']:r for r in bridge['rows']}
    matching=[]
    for r in motion['rows']:
        terms=('rebuild','translation','contact','suspension','centroid_rounding','post_centroid')
        assert [sum(r[k][i] for k in terms) for i in range(3)]==r['total']
        assert [r['final_position'][i]-r['initial_position'][i] for i in range(3)]==r['total']
        if r['tick'] in bytick:
            expected=bytick[r['tick']]
            assert r['final_position']==[expected[k] for k in ('x','y','z')]
            matching.append(r['tick'])
    paths[hz]=[r for r in bridge['rows'] if 15.4<=r['tick']/hz<=16]
    report[str(hz)]=dict(motion_capture=motion_name,bridge_capture=bridge_name,updates=len(motion['rows']),matching_body_positions=len(matching),motion_sha256=hashlib.sha256((cap/'landing-motion-check.json').read_bytes()).hexdigest(),slave_sha256=hashlib.sha256((cap/'slave.slave').read_bytes()).hexdigest(),
        contact_sequence=[dict(time=r['tick']/hz,preupdate_pitch=(r['angles'][1]+32768)%65536-32768,preupdate_extensions=r['extension'],preupdate_velocities=r['wheel_velocity']) for r in motion['rows'] if 15.5<=r['tick']/hz<=15.75])
rows=[]
for native in paths[20]:
    t=native['tick']/20
    simultaneous=next(r for r in paths[50] if r['tick']==round(t*50)) if native['tick']%2==0 else None
    for a,b in zip(paths[50],paths[50][1:]):
        assert b['z']>a['z']
        if a['z']<=native['z']<=b['z']:
            f=(native['z']-a['z'])/(b['z']-a['z'])
            pitch=a['pitch']+f*(b['pitch']-a['pitch'])
            rows.append(dict(native_time=t,native_pitch=native['pitch'],matched_time=(a['tick']+f)/50,matched_pitch=pitch,matched_pitch_error=pitch-native['pitch'],common_time_pitch_error=None if simultaneous is None else simultaneous['pitch']-native['pitch'],bracketing_ticks=[a['tick'],b['tick']]))
            break
critical=next(r for r in rows if r['native_time']==15.6)
assert critical['native_pitch']==-7 and critical['common_time_pitch_error']==-20
out=dict(captures=report,spatial_comparison=rows,critical=critical,scope='All measured motion terms telescope to actual body displacement; overlapping final positions match independent full-course captures. Spatial interpolation is offline description only and never changes the common-time gate. Stage named contact includes all motion between native boundaries, not necessarily collision alone. Suspension and velocity observations are PRE-update; full-course pitch is POST-update. Native reference predates the ABI8 contact-return change, which affects only50Hz.',conclusions=['Equal-Z alignment reduces the 15.6s pitch difference but does not remove it; inspect the saved numeric critical record.', 'The baseline front extensions retract384->256->128->0 before rear retraction starts. Native20 retains front128 while rear begins retracting. These are different observed contact sequences, not a proven isolated cause.', 'Next inspect front/rear clearance and contact decisions around15.54..15.66 with correct pre/post timing, before changing angular response.'])
(P/'baseline-landing-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(matches={h:r['matching_body_positions'] for h,r in report.items()},critical=critical),indent=2))
