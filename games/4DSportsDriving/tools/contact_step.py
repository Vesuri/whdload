"""Validated straight contact subsystem with externally prescribed distance."""
from copy import deepcopy
from native_contact_response import rotate,sine
from contact_body_predictor import body as body50
from native20_contact_model import body as body20
from crest_terrain_query import query

def step(state,hz,distance,roof=None,impact=None,body_solver=None,movement_matrix=None):
    assert hz in (10,20,50)
    state=deepcopy(state);e=state['entry'];position=state['position'];cached=state['cached']
    roof=roof or [0]*4;impact=impact or [0]*4
    t=e[0];pitch=e[2];sn,cs=sine(pitch),sine(pitch+256);e[4:13]=[16384,0,0,0,cs,-sn,0,sn,cs]
    build=[[x,-384-e[13+w],z] for w,(x,z) in enumerate(((-960,1984),(960,1984),(960,-1984),(-960,-1984)))];rows=[]
    delta=rotate([0,0,distance],e[4:13] if movement_matrix is None else movement_matrix)
    for w in range(4):
        old=[p+v for p,v in zip(position,rotate(build[w],e[4:13]))];new=[x+y for x,y in zip(old,delta)]
        e[45+3*w:48+3*w]=old;e[57+3*w:60+3*w]=new
        row=query(new,cached[w]);row.update(tick=t,wheel=w,distance=distance,correction=roof[w],impact_flags=impact[w])
        for key,offset in (('extension',13),('velocity',21),('velocity_fraction',25),('position_fraction',29),('extension_fraction',33)):row[key]=e[offset+w]
        row.update({'old_world_'+a:v for a,v in zip('xyz',old)});row.update({'world_'+a:v for a,v in zip('xyz',new)});rows.append(row)
    out=body_solver(e,build,rows,state) if body_solver else (body50(e,build,rows) if hz==50 else body20(e,build,rows,hz=hz))
    before=e.copy();state['position']=out['position'];e[2]=out['pitch'];e[41]=out['pitch_carry'];e[42:45]=out['centroid_carries']
    for w,(wheel,su) in enumerate(zip(out['wheels'],out['suspensions'])):
        cached[w]=[x>>6 for x in wheel['position']]
        for offset,key in ((13,'extension'),(17,'bias'),(33,'ef'),(37,'bf')):e[offset+w]=su[key]
        for offset,key in ((21,'velocity'),(25,'vf'),(29,'pf')):e[offset+w]=wheel[key]
    e[0]+=1
    return state,dict(entry=before,build=build,selected=rows,output=out)
