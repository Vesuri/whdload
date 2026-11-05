"""Scoped straight-lane native query, including cached-position conditions.

Map/descriptor inputs come from the canonical pre-window snapshot. Node records
are fixed constants checked across all920 read-only queries. This module rejects
barrier response, out-of-lane and unsupported terrain rather than extrapolating.
"""
import json
from crest_surface_selector_check import select,word,read,a4,ROOT
from native_contact_response import plane,UnsupportedContact
nodes={int(k):v for k,v in json.loads((ROOT/'tmp/prof/terrain-query-check.json').read_text())['constant_nodes'].items()}
def query(world,cached):
    if len(world)!=3 or len(cached)!=3:raise ValueError('XYZ required')
    s=select(world)
    x,y,z=[word(v>>6) for v in world]
    lx,lz=word(x-s['base_x']),word(z-s['base_z'])
    ox,oz=word(cached[0]-s['base_x']),word(cached[2]-s['base_z'])
    if s['orientation']==512:lx,lz,ox,oz=[word(-v) for v in (lx,lz,ox,oz)]
    if abs(lx)>=120 or abs(ox)>=120:raise UnsupportedContact('New and cached positions must stay inside strict centre lane')
    barrier=-1;flags=1
    if s['kind']==16:
        if lz>0:flags=0
        elif oz>=0:barrier=102
    surface=max(1,read(a4-0x5b0c+20*s['track']+15,'b')+1)
    node=nodes[s['plane']]
    r={k:s[k] for k in ('plane','base_x','base_y','base_z')}
    for i,axis in enumerate('xyz'):
        r['node_'+axis]=node[2+i];r['normal_'+axis]=node[5+i]
        r['origin_'+axis]=word(r['base_'+axis]+r['node_'+axis])
    r.update({'matrix'+str(i):v for i,v in enumerate(node[8:])})
    r.update(plane_flags=flags,barrier=barrier,surface=surface)
    r['clearance']=plane(r,world)
    if barrier>=0 and -1000<r['clearance']<-12:raise UnsupportedContact('Native barrier response required')
    return r
