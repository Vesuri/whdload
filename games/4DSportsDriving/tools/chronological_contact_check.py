#!/usr/bin/env python3
"""Audit ballistic free-flight equivalence and event timing on captured inputs."""
import json,struct,collections
from pathlib import Path
from chronological_contact_model import advance
from contact_body_predictor import wheel
from native_contact_response import UnsupportedContact
root=Path('tmp/prof');report=[]
for name in ('contact-prediction-d9-long','contact-prediction-d9-minus64-long','contact-prediction-d9-plus64-long'):
    cap=root/name;r=json.loads((cap/'prediction.json').read_text())['records'];m=json.loads((cap/'anchor.json').read_text());ram=(cap/'memory.bin').read_bytes();car=m['data_base']+0x7ffe-0x92e-m['memory_base']
    finals={(v[0],v[1]):v[2:5] for v in r['FINAL']};stats=collections.Counter();unsupported=[];max_v=max_pf=0.
    for row in r['SELECT']:
        t,w=row['tick'],row['wheel'];cache=list(struct.unpack_from('>3h',ram,car+0x74+6*w)) if t==451 else [v>>6 for v in finals[t-1,w]]
        try:out=advance(row,cache)
        except UnsupportedContact as e:unsupported.append(dict(tick=t,wheel=w,reason=str(e)));continue
        stats[out['branch']]+=1;events=out['events'];times=[e['time'] for e in events]
        assert all(-1e-10<=t<=1+1e-10 for t in times) and times==sorted(times)
        if out['branch']=='air' and events and all(e['clearance']>0 for e in events):
            native=wheel(row)
            if native['branch']!='air':stats['continuous_air_native_contact']+=1;continue
            assert out['position']==native['position'],(name,t,w,out['position'],native['position'])
            dv=abs(out['velocity']+out['vf']/5-native['velocity']-native['vf']/5)
            dp=abs(out['pf']-native['pf']);assert dv<1e-7 and dp<1e-6,(t,w,dv,dp)
            max_v=max(max_v,dv);max_pf=max(max_pf,dp);stats['exact_free_flight_position']+=1
    report.append(dict(capture=name,counts=dict(stats),unsupported=unsupported,max_free_velocity_error=max_v,max_free_position_carry_error=max_pf))
(root/'chronological-contact-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
