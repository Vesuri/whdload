"""Experimental support constraint preserving the acquired contact depth.

Depth is acquired from the actual native contact endpoint, never a reference
trajectory or a fitted constant. Constraint stops on surface change/separation.
This is an offline candidate, not an accepted replacement contact law.
"""
from native_contact_response import word
from contact_body_predictor import body,wheel
from crest_terrain_query import query
from supported_plane_model import geometry,dot

def project(position,origin,normal,target):
    depth=dot(position,origin,normal)-target;norm=sum(n*n for n in normal)
    assert depth<=0 and normal[1]>0 and norm>0
    out=[x+((-2*n*depth+norm)//(2*norm)) for x,n in zip(position,normal)]
    residual=dot(out,origin,normal)-target
    if residual<0:out[1]+=(-residual+normal[1]-1)//normal[1]
    residual=dot(out,origin,normal)-target;assert residual>=0
    return out,residual

def solve(entry,build,rows,state,require_resting=False):
    support=state.setdefault('anchored_support',[None]*4)
    def constrained(row):
        w=row['wheel'];key=geometry(row);origin=[word(row['base_'+a]+row['node_'+a]) for a in 'xyz'];normal=[row['normal_'+a] for a in 'xyz'];new=[row['world_'+a] for a in 'xyz'];active=support[w]
        inherited=(active is not None and active['surface']==key and row['velocity']==row['velocity_fraction']==row['correction']==0 and dot(new,origin,normal)<=active['target'])
        if inherited:
            old=new.copy();new,residual=project(new,origin,normal,active['target'])
            fresh=query(new,state['cached'][w]);assert geometry(fresh)==key,'Projection crossed a terrain boundary'
            result=dict(position=new,clearance=0,suspension_clearance=0,velocity=0,vf=0,pf=0,ef=0,branch='anchored_support',applied_gravity=False,down=0,analytic_residual=residual,
                target=active['target'],constraint_delta=[x-y for x,y in zip(new,old)],native_query_after_projection=fresh['clearance'])
        else:
            result=wheel(row)
            support[w]=None
            if result['branch']!='air':
                endpoint=query(result['position'],state['cached'][w])
                result['acquisition_endpoint_clearance']=endpoint['clearance']
                eligible=not require_resting or (endpoint['clearance']==0 and geometry(endpoint)==key)
                if eligible:support[w]=dict(surface=key,target=dot(result['position'],origin,normal))
        return result
    return body(entry,build,rows,wheel_solver=constrained)

def solve_resting(entry,build,rows,state):
    return solve(entry,build,rows,state,require_resting=True)
