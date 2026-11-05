#!/usr/bin/env python3
"""Same-state100ms contact comparison, equal prescribed total forward distance."""
import json,struct,hashlib,collections,sys
from supported_plane_model import solve
endpoint='--endpoint' in sys.argv
anchored='--anchored' in sys.argv
supported='--supported' in sys.argv or anchored or endpoint
if anchored:
 from anchored_support_model import solve
if endpoint:
 from endpoint_force_model import solve
from copy import deepcopy
from pathlib import Path
from contact_step import step
root=Path('tmp/prof');cap=root/'native20-contact-model'
r=json.loads((cap/'prediction.json').read_text())['records'];meta=json.loads((cap/'anchor.json').read_text());memory=(cap/'memory.bin').read_bytes()
car=meta['data_base']+0x7ffe-0x92e-meta['memory_base'];initial_cached=[list(struct.unpack_from('>3h',memory,car+0x74+6*w)) for w in range(4)]
canonical={v['tick']:v for v in json.loads((root/'natural-crest20/bridge.json').read_text())['rows']}
final={(v[0],v[1]):v[2:5] for v in r['FINAL']};selected={(v['tick'],v['wheel']):v for v in r['SELECT']}
def run(seed,hz,distance,impact):
    state=deepcopy(seed);rem=0;history=[]
    for _ in range(hz//10):
        d=distance
        if hz==50:d,rem=divmod(2*distance+rem,5)
        state,record=step(state,hz,d,impact=impact,body_solver=solve if supported and hz==50 else None)
        out=record['output']
        history.append(dict(distance=d,position=out['position'],pitch=out['pitch'],pitch_carry=out['pitch_carry'],
            planes=[v['plane'] for v in record['selected']],clearances=[v['clearance'] for v in record['selected']],
            branches=[v['branch'] for v in out['wheels']],velocity_fifths=[5*v['velocity']+v['vf'] for v in out['wheels']],
            extension=[v['extension'] for v in out['suspensions']],returned=[v['returned'] for v in out['suspensions']]))
    assert rem==0 and sum(v['distance'] for v in history)==2*distance
    return state,history
rows=[]
for observed in r['ENTRY']:
    t=observed[0];previous=canonical[t-1];position=[previous[k] for k in ('x','y','z')]
    cached=initial_cached if t==181 else [[v>>6 for v in final[t-1,w]] for w in range(4)]
    assert observed[25:45]==[0]*20
    seed=dict(entry=observed.copy(),position=position,cached=deepcopy(cached))
    preserved=deepcopy(seed);distance=selected[t,0]['distance'];impact=[selected[t,w]['impact_flags'] for w in range(4)]
    assert all(selected[t,w]['correction']==0 for w in range(4))
    a,ha=run(seed,20,distance,impact);b,hb=run(seed,50,distance,impact);assert seed==preserved
    error=dict(position=[y-x for x,y in zip(a['position'],b['position'])],pitch=b['entry'][2]-a['entry'][2],
        velocity_fifths=[5*(b['entry'][21+w]-a['entry'][21+w])+b['entry'][25+w] for w in range(4)],
        extension=[b['entry'][13+w]-a['entry'][13+w] for w in range(4)])
    rows.append(dict(seed_tick=t,seed_time=(t-1)/20,distance=distance,initial_position=position,initial_pitch=observed[2],
        initial_velocity=observed[21:25],initial_extension=observed[13:17],error=error,native20=ha,a4000=hb))
summary=dict(cases=len(rows),unequal_final_velocity_cases=sum(any(x['error']['velocity_fifths']) for x in rows),
 max_abs_y=max(abs(x['error']['position'][1]) for x in rows),max_abs_pitch=max(abs(x['error']['pitch']) for x in rows))
report=dict(endpoint_force_correction=endpoint,supported_constraint=supported,anchored_constraint=anchored,summary=summary,rows=rows,scope='Same native physical start,2x50ms vs5x20ms, identical total forward distance and held initial roof/impact inputs. Re-query and rebuild every step; no recorded subsequent states. Exact validated subsystem, not full engine/controller or live changed-rate acceptance.')
(root/('contact-equal-time-endpoint.json' if endpoint else 'contact-equal-time-anchored.json' if anchored else 'contact-equal-time-supported.json' if supported else 'contact-equal-time.json')).write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps(summary))
for row in rows:
 if 215<=row['seed_tick']<=228:print(row['seed_tick'],row['error'])
