#!/usr/bin/env python3
"""Check whether retaining existing Q8 pitch removes coupling discontinuities.

Only the correction direction calculation uses the existing sub-angle residue;
wheel reconstruction and native matrices remain unchanged. Sine-table linear
interpolation here approximates an angle, never a previous rendered frame.
"""
import json,collections
from coupled_movement_check import ROOT,r,predict,selected
from native_contact_response import sine

def sine_q8(angle):
    integer,fraction=divmod(angle,256)
    return (256-fraction)*sine(integer)+fraction*sine(integer+1)

def main():
    records=[]
    for entry in r['ENTRY']:
        old=entry[2]*256+entry[41];distance=selected[entry[0],0]['distance']
        correction=[0,0,0];seen=set();steps=[];status='limit'
        for iteration in range(32):
            key=tuple(correction)
            if key in seen:status='cycle';break
            seen.add(key)
            try:out=predict(entry,correction)
            except Exception as exc:status='unsupported';steps.append(dict(correction=correction,error=repr(exc)));break
            new=out['pitch']*256+out['pitch_carry']
            target=[0]+[3*distance*(sine_q8(old+axis)-sine_q8(new+axis))//(65536*256) for axis in (0,256*256)]
            steps.append(dict(correction=correction,result_pitch=out['pitch'],result_carry=out['pitch_carry'],target=target,branches=[w['branch'] for w in out['wheels']]))
            if target==correction:status='fixed';break
            correction=target
        records.append(dict(tick=entry[0],status=status,steps=steps))
    report=dict(counts=dict(collections.Counter(x['status'] for x in records)),max_iterations=max(len(x['steps']) for x in records),rows=records,
      scope='Independent original states, zero translation carry. Q8 direction correction only, no fractional native geometry changes. Tests whether published-angle rounding alone explains coupling cycles; no corrected trajectory/handling claim.')
    (ROOT/'tmp/prof/coupled-fractional-direction-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ('rows','scope')});print('nonfixed',[(x['tick'],x['status']) for x in records if x['status']!='fixed'])
if __name__=='__main__':main()
