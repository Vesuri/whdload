#!/usr/bin/env python3
"""P7 mechanistic endpoint-rate correction and specified release-age screen."""
import p7_offline
import json,struct,hashlib
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import coupled_vehicle_core as core
import contact_body_predictor as model
from simulation_fixture import read_fixture
from native_contact_response import plane,word
OUT=p7_offline.OUT
orig_engine=core.engine
orig_wheel=model.wheel

def engine(car,carry,param,read,**kw):
    old=struct.unpack_from('>H',car,0x2c)[0]*1408//15360
    result,c,rec=orig_engine(car,carry,param,read,**kw)
    if kw['hz']==50:
        new=struct.unpack_from('>H',result,0x2c)[0]*1408//15360
        extra,c['endpoint_fraction']=divmod(3*(new-old)+carry.get('endpoint_fraction',0),10)
        rec['distance']+=extra
        rec['endpoint_correction']=extra
    return result,c,rec

def wheel(r):
    # Replace only first zero-velocity airborne pair; all contact reset/response stays original.
    if r['velocity']==0 and r['velocity_fraction']==0 and r['clearance']>0:
        h5=(2*r['tick'])%5 or 5
        a=21 if r['wheel']<2 else 15
        dv,vf=divmod(h5*a,5)
        dy,pf=divmod(h5*(h5+5)//2*a+r['position_fraction'],25)
        # The original wheel applies its 2/5 recurrence; supply a local equivalent
        # starting state to get exactly the desired dv/dy, then preserve normal response.
        # Use an explicit original-function copy, modifying only the recurrence.
        return release_wheel(r,h5)
    return orig_wheel(r)

# Keep the identical independently validated contact body, altering only first-step h.
import inspect
source=inspect.getsource(orig_wheel).replace('def wheel(r):','def release_wheel(r,h5):')
source=source.replace('10*v+2*vf+7*a+pf','5*h5*v+h5*vf+h5*(h5+5)//2*a+pf').replace('2*a+vf','h5*a+vf')
exec(source,model.__dict__)
release_wheel=model.release_wheel

def initial(cap):
    b,read,param=core.seed(cap)
    tick,hz,s=read_fixture(cap)[0];assert tick==0
    car=bytearray(s[0x152:0x152+208]);unpack=lambda fmt,o:list(struct.unpack_from('>'+fmt,car,o))
    e=[1]+unpack('3h',0x18)+[0]*9+unpack('4h',0x54)+unpack('4h',0x6c)+unpack('4h',0x4c)+[0]*44
    assert len(e)==69
    b=dict(car=car,carry=dict(acceleration=0,distance=0,gear=0),contact=dict(entry=e,position=unpack('3i',0),cached=[unpack('3h',0x74+6*w) for w in range(4)]))
    return b,read,param

def run(phase,mode):
    cap=Path('tmp/prof')/('crest-d9e7903' if phase=='nominal' else 'phase-'+phase+'-d9')
    b,read,param=initial(cap);rows=[]
    baseline=json.loads((OUT/('coupled-course-baseline'+('' if phase=='nominal' else '-'+phase)+'.json')).read_text())['rows'];ix={r['tick']:r for r in baseline}
    with patch.object(core,'engine',engine if mode!='control' else orig_engine),patch.object(model,'wheel',wheel if mode=='combined' else orig_wheel):
        for t in range(1,801):
            b,rec=core.advance(b,50,read,param,solver=(lambda e,build,rows,state:model.body(e,build,rows,wheel_solver=model.wheel)))
            s=core.summarize(b);row=dict(tick=t,**dict(zip(('x','y','z'),s.pop('position'))),**s,distance=rec['engine']['distance'],carry=b['carry'].copy())
            if mode=='control' and t in ix:
                for k in ('x','y','z','pitch','speed','target','rpm','gear','clutch','flags','distance','carry'):assert row[k]==ix[t][k],(phase,t,k,row[k],ix[t][k])
            rows.append(row)
    out=dict(mode=mode,phase=phase,rows=rows,exact_control_steps=795 if mode=='control' else 0)
    (OUT/f'{mode}-{phase}.json').write_text(json.dumps(out,indent=2)+'\n')
    return rows

if __name__=='__main__':
    for phase in ('nominal','minus64','plus64'):
        control=run(phase,'control');distance=run(phase,'distance')
        assert [r['speed'] for r in control[:450]]==[r['speed'] for r in distance[:450]]
        native=json.loads((OUT/('coupled-course20-baseline'+('' if phase=='nominal' else '-'+phase)+'.json')).read_text())['rows']
        z20=next(r['z'] for r in native if r['tick']==180)
        print(phase,'Z9',control[449]['z']-z20,'->',distance[449]['z']-z20,flush=True)
        assert abs(distance[449]['z']-z20)<=60
        run(phase,'combined')
