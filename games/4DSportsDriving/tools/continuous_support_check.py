#!/usr/bin/env python3
import json,math
from pathlib import Path
from continuous_support_reference import integrate,plane

def row(y,dy,z=100,dz=200,v=0,normal=(0,8192,0),distance=200):
    r={f'{p}{a}':0 for p in ('base_','node_') for a in 'xyz'}
    r.update(dict(zip(('normal_x','normal_y','normal_z'),normal)))
    r.update(plane=4,wheel=0,velocity=v,velocity_fraction=0,distance=distance,old_world_x=0,old_world_y=y,old_world_z=z,world_x=0,world_y=y+dy,world_z=z+dz)
    return r
results=[]
for r in (row(0,0),row(-3,0),row(100,10),row(3,-10),row(100,100,normal=(0,8192,-4096)),row(50,100,normal=(0,8192,-4096))):
    out=integrate(r);assert abs(out['time_sum']-1)<1e-12
    assert out['clearance_units']>=-1e-8
    if out['supported']:
        n=plane(r)['normal'];normal_speed=n[1]*((r['world_y']-r['old_world_y'])-.4*(out['velocity']+10.5))+n[2]*(r['world_z']-r['old_world_z']);assert abs(normal_speed)<1e-7
    # Pure support must travel exactly the issued arc distance after projection.
    if all(e['supported'] for e in out['events']):
        start=[r['old_world_'+a] for a in 'xyz']
        for p in out['projections']:start=[a+b for a,b in zip(start,p['vector'])]
        assert abs(math.dist(start,out['position'])-r['distance'])<1e-9
    # Same physical interval split into two equal spans must compose.
    half=dict(r);half['distance']/=2
    for axis in 'xyz':half['world_'+axis]=(r['old_world_'+axis]+r['world_'+axis])/2
    first=integrate(half,step_h=.2);second=dict(half);second['velocity']=first['velocity'];second['velocity_fraction']=0
    for index,axis in enumerate('xyz'):
        second['old_world_'+axis]=first['position'][index]
        second['world_'+axis]=first['position'][index]+(r['world_'+axis]-r['old_world_'+axis])/2
    final=integrate(second,step_h=.2)
    assert math.dist(out['position'],final['position'])<1e-8 and abs(out['velocity']-final['velocity'])<1e-8,(r,out,final)
    results.append(dict(input=r,result=out,partition_exact=True))
# Pure airborne case agrees analytically with the existing fractional pair.
r=row(100,10);out=integrate(r);assert abs(out['velocity']-8.4)<1e-12;assert abs(out['position'][1]-(110-21*.4*1.4/2))<1e-12
Path('tmp/prof/continuous-support-check.json').write_text(json.dumps({'cases':results,'scope':'Independent time/nonpenetration/arc-distance invariants and free-flight analytic check for a new diagnostic law, not native handling acceptance.'},indent=2)+'\n')
print('Continuous support invariants:',len(results),'cases; pure-air ordered flow exact')
