#!/usr/bin/env python3
import json,struct,re
from pathlib import Path
from airborne_pitch_predictor import predict
from native_contact_response import sine
P=Path('tmp/prof/matched-flight50');m=json.loads((P/'anchor.json').read_text());mem=(P/'memory.bin').read_bytes()
priv=mem.index(b'4DA4PHYS')+12
vf=[struct.unpack_from('>h',mem,priv+8+4*w)[0] for w in range(4)]
pf=[struct.unpack_from('>h',mem,priv+10+4*w)[0] for w in range(4)]
carry=struct.unpack_from('>h',mem,priv+144)[0]
rows=json.loads((P/'landing-motion-check.json').read_text())['rows']
raw={int(v[0]):list(map(int,v)) for v in [line.split()[1:] for line in (P/'landing-motion.txt').read_text().splitlines() if line.startswith('REBUILD ')]}
checks=[];residue=0;correction=0
distance_carry=struct.unpack_from('>h',mem,priv+4)[0]
for i,r in enumerate(rows):
    assert r['extension']==[384]*4 and r['angles'][0]==r['angles'][2]==0
    out=predict(r['wheel_stages']['rebuilt'],r['wheel_velocity'],vf,pf,carry)
    actual=[r['wheel_stages']['translated'][w][1]-r['wheel_stages']['contact'][w][1] for w in range(4)]
    assert out['downward']==actual
    if i+1<len(rows):
        expected=(rows[i+1]['angles'][1]+32768)%65536-32768
        assert out['pitch']==expected,(r['tick'],out,expected)
        assert out['velocities']==rows[i+1]['wheel_velocity']
    q=raw[r['tick']][14]*1408//15360;distance,distance_carry=divmod(q*2+distance_carry,5)
    old=(r['angles'][1]+32768)%65536-32768
    assert r['translation']==[0,distance*sine(old)//16384,distance*sine(old+256)//16384]
    # h=.02,T=.05: -(T-h)/(2h) times the within-step direction change.
    n=3*distance*(sine(old)-sine(out['pitch']))
    dy,residue=divmod(n+residue,65536);correction+=dy
    checks.append(dict(tick=r['tick'],prediction=out,leading_order_y_correction=dy,cumulative_y_correction=correction))
    vf=out['velocity_fifths'];pf=out['position_twentyfifths'];carry=out['carry']
report=dict(exact_gravity_steps=len(rows)*4,exact_next_pitch_predictions=len(rows)-1,exact_movement_vectors=len(rows),rows=checks,
 scope='Predictor uses only pre-contact rebuilt wheel geometry, current gravity carries and angle carry. Fully extended straight airborne domain; no future trace data is an input. Leading-order ordering correction is attribution only until a verified live run.')
Path('tmp/prof/airborne-pitch-predictor-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Exact gravity steps',len(rows)*4,'next pitch predictions',len(rows)-1,'movement vectors',len(rows),'cumulative proposed Y',correction)
