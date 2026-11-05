"""Experimental remembered-surface constraint, never a production fallback.

After a native contact, same-surface zero-gravity penetration is projected onto
the analytic plane. New contacts and release use the existing solver. State is
four support-surface identities; target geometry is plane zero, not a fitted
trajectory. Includes no native20 simulation or reference impulse.
"""
from native_contact_response import word
from contact_body_predictor import body,wheel
from crest_terrain_query import query

def geometry(row):
    return tuple(row[k] for k in ('plane','base_x','base_y','base_z','node_x','node_y','node_z','normal_x','normal_y','normal_z'))
def dot(position,origin,normal):return sum((x-64*o)*n for x,o,n in zip(position,origin,normal))
def project(position,origin,normal):
    depth=dot(position,origin,normal);norm=sum(n*n for n in normal)
    assert depth<=0 and normal[1]>0 and norm>0
    # Closest point on analytic plane, nearest integer then minimal upwards
    # repair for rounding. Last repair is less than one raw Y coordinate.
    out=[x+((-2*n*depth+norm)//(2*norm)) for x,n in zip(position,normal)]
    residual=dot(out,origin,normal)
    if residual<0:out[1]+=(-residual+normal[1]-1)//normal[1]
    residual=dot(out,origin,normal);assert residual>=0
    return out,residual

def solve(entry,build,rows,state):
    support=state.setdefault('support',[None]*4)
    def constrained(row):
        w=row['wheel'];key=geometry(row);origin=[word(row['base_'+a]+row['node_'+a]) for a in 'xyz'];normal=[row['normal_'+a] for a in 'xyz'];new=[row['world_'+a] for a in 'xyz']
        inherited=(support[w]==key and row['velocity']==row['velocity_fraction']==row['correction']==0 and dot(new,origin,normal)<=0)
        if inherited:
            unconstrained=new.copy();new,residual=project(new,origin,normal)
            fresh=query(new,state['cached'][w]);assert geometry(fresh)==key,'Projection crossed a terrain boundary'
            result=dict(position=new,clearance=0,suspension_clearance=0,velocity=0,vf=0,pf=0,ef=0,branch='supported_plane',applied_gravity=False,down=0,analytic_residual=residual,constraint_delta=[x-y for x,y in zip(new,unconstrained)],native_query_after_projection=fresh['clearance'])
        else:result=wheel(row)
        support[w]=key if result['branch']!='air' else None
        return result
    return body(entry,build,rows,wheel_solver=constrained)
