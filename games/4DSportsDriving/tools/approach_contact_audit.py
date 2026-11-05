#!/usr/bin/env python3
"""Account for the contact changes in the position-only intervention."""
import json,hashlib
from pathlib import Path
from native_contact_response import resolve,vec
from simulation_fixture import read_fixture
root=Path('tmp/prof');report={}
for name in ('control','native-position'):
    cap=root/f'approach550-contact-{name}'
    original=root/f'approach550-{name}'
    assert (cap/'slave.slave').read_bytes()==(original/'slave.slave').read_bytes()
    assert read_fixture(cap)==read_fixture(original)
    groups={}
    for r in json.loads((cap/'penetration.json').read_text())['rows']:
        group=groups.setdefault((r['tick'],r['wheel']),{})
        assert r['stage'] not in group
        group[r['stage']]=r
    results=[]
    for key,stages in groups.items():
        r=stages['ROTATED'];done=stages['DONE']
        # These observed contacts precede airborne acceleration, so the
        # native word and actual per-tick downward displacement are both zero.
        assert r['velocity']==0
        result=resolve(vec(r,'old'),vec(r,'new'),r,r['distance'],0,0,r['impact_flags'])
        assert result['position']==vec(stages['RESOLVED'],'new')==vec(done,'new')
        assert result['velocity']==done['velocity'] and result['stored_clearance']==done['clearance']
        assert result['impact_flags']==done['impact_flags']
        if 'PUSH_VECTOR' in stages: assert result['push']==vec(stages['PUSH_VECTOR'],'correction')
        results.append(dict(tick=key[0],wheel=key[1],plane=r['plane'],old_plane_y=r['old_plane_y'],new_plane_y=r['new_plane_y'],entry_clearance=stages['ENTER']['clearance'],**result))
    report[name]={'source_sha256':hashlib.sha256((cap/'penetration.json').read_bytes()).hexdigest(),'initial_state_exact':True,'contacts':results}
report['scope']='Exact independent native-response reconstruction for the recorded zero-velocity contacts. Position-only intervention does not preserve contact clearance. No runtime correction or general rate-independence claim.'
(root/'approach550-contact-audit.json').write_text(json.dumps(report,indent=2)+'\n')
for name in ('control','native-position'):
    print(name,[(r['tick'],r['wheel'],r['entry_clearance'],r['old_plane_y'],r['new_plane_y'],r['branch'],r.get('push')) for r in report[name]['contacts']])
