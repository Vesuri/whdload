#!/usr/bin/env python3
"""Offline self-consistency diagnostic, not an accepted contact integration law.

The smooth-flight leading ordering term is c=3D(u_old-u_next)/4, in native
Q14 directions. Here u_next is predicted after applying c and fresh terrain
queries. Each recorded step is independent, with zero correction carry; this
is NOT a simulated corrected trajectory or a handling comparison.
"""
import json,collections
from pathlib import Path
from crest_terrain_query import query
from contact_body_predictor import body
from native_contact_response import sine
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'tmp/prof/terrain-motion-identity'
r=json.loads((p/'prediction.json').read_text())['records']
build={(x[0],x[1]):x[2:] for x in r['BUILD']}
cached={(x[0],x[1]):x[2:] for x in r['CACHED']}
selected={(x['tick'],x['wheel']):x for x in r['SELECT']}

def predict(entry,correction):
    entry=entry.copy();rows=[];tick=entry[0]
    for w in range(4):
        for axis in range(3):entry[57+3*w+axis]+=correction[axis]
        world=entry[57+3*w:60+3*w]
        row=dict(selected[tick,w]);row.update(query(world,cached[tick,w]))
        row.update({'world_'+a:v for a,v in zip('xyz',world)})
        rows.append(row)
    return body(entry,[build[tick,w] for w in range(4)],rows)

def correction(entry,pitch):
    old=entry[2];distance=selected[entry[0],0]['distance']
    assert all(selected[entry[0],w]['distance']==distance for w in range(4))
    return [0,3*distance*(sine(old)-sine(pitch))//65536,
              3*distance*(sine(old+256)-sine(pitch+256))//65536]

def main():
    records=[]
    for entry in r['ENTRY']:
        pitch=entry[2];seen={};steps=[];status='limit'
        for iteration in range(32):
            if pitch in seen:status='cycle';break
            seen[pitch]=iteration;c=correction(entry,pitch)
            try:out=predict(entry,c)
            except Exception as exc:status='unsupported';steps.append(dict(pitch=pitch,correction=c,error=repr(exc)));break
            steps.append(dict(pitch=pitch,correction=c,result_pitch=out['pitch'],branches=[w['branch'] for w in out['wheels']]))
            if pitch==out['pitch']:status='fixed';break
            pitch=out['pitch']
        records.append(dict(tick=entry[0],old_pitch=entry[2],status=status,steps=steps))
    report=dict(counts=dict(collections.Counter(x['status'] for x in records)),max_iterations=max(len(x['steps']) for x in records),rows=records,
        scope='Independent recorded starting states, zero correction carry. Fixed-point iteration of smooth-flight ordering formula extended to contact as a diagnostic. Fresh terrain queries each evaluation. No corrected trajectory, valid nonsmooth contact-law derivation, or handling/capacity gate.')
    (ROOT/'tmp/prof/coupled-movement-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ('rows','scope')})
    print('nonfixed',[(x['tick'],x['status'],[(s['pitch'],s.get('result_pitch')) for s in x['steps']]) for x in records if x['status']!='fixed'])
if __name__=='__main__':main()
