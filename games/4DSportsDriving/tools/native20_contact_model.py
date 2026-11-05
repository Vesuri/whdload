"""Native A2500 wheel/suspension reference; exact discrete20Hz semantics."""
from native_contact_response import plane,resolve,rotate,word,atan_native,UnsupportedContact
from airborne_pitch_predictor import atan_q8,axis,wrap
def trunc(n,d):return abs(n)//d*(1 if n>=0 else -1)
def suspension(extension,bias,clearance,ef,bf):
    old=extension
    if bias:
        step=4 if bias<0 else -4;bf=0
        updated=bias+step
        if bias<0 and updated>=0 or bias>0 and updated<=0:bias=bf=0
        else:bias=updated
    else:bf=0
    c=clearance
    if c<0 and -c<extension:c=0
    adjustment=0
    if c==0:
        if extension>bias:
            extension=max(bias,word(extension-128));adjustment=word(old-extension)
        elif extension<bias:extension=min(bias,word(extension+128))
    elif c>0:
        step=min(c,192);ef=0
        extension=word(extension+step)
        if extension>=384:extension=384;ef=0
    else:
        if word(extension+c)>-288:extension=word(extension+c)
        else:extension=max(-384,word(extension+(word(c*3)>>2)))
        adjustment=word(word(old-extension)+c)
    return dict(returned=word(old+adjustment),extension=extension,bias=bias,ef=ef,bf=bf,branch_clearance=c)
def wheel(r,hz=20):
    assert hz in (10,20)
    if r['correction']!=0:raise UnsupportedContact('Roof correction domain not supported')
    old=[r['old_world_'+a] for a in 'xyz'];new=[r['world_'+a] for a in 'xyz']
    geo={k:r[k] for k in ('plane','plane_flags','normal_x','normal_y','normal_z',*('matrix'+str(i) for i in range(9)))}
    geo.update({'origin_'+a:word(r['base_'+a]+r['node_'+a]) for a in 'xyz'})
    q=plane(geo,new);assert q==r['clearance']
    v=r['velocity'];vf=r['velocity_fraction'];pf=r['position_fraction'];ef=r['extension_fraction']
    applied=q>0;down=0
    if applied:
        a=21 if r['wheel']<2 else 15
        for _ in range(2 if hz==10 else 1):
            v=word(v+a);down+=v
        pf=vf=0;new[1]-=down
        q=plane(geo,new)
    suspension_clearance=q
    if q<0:
        ratio=v
        out=resolve(old,new,geo,r['distance'],ratio,v,r['impact_flags'])
        new=out['position'];q=out['stored_clearance'];branch=out['branch']
    else:branch='zero' if q==0 else 'air'
    if branch!='air':v=vf=pf=ef=0
    return dict(position=new,clearance=q,suspension_clearance=suspension_clearance,velocity=v,vf=vf,pf=pf,ef=ef,branch=branch,applied_gravity=applied,down=down)

def body(entry,build,selected,hz=20):
    if entry[1] or entry[3]:raise UnsupportedContact('Straight domain required')
    ends=[wheel(row,hz) for row in selected]
    susp=[suspension(entry[13+w],entry[17+w],ends[w]['suspension_clearance'],0,0) for w in range(4)]
    basis=[[x+y for x,y in zip(ends[w]['position'],rotate([0,384+susp[w]['returned'],0],entry[4:13]))] for w in range(4)]
    position=[sum(v[i] for v in basis)//4 for i in range(3)]
    pitch=atan_native(*axis(basis))-256
    if abs(pitch)<2:pitch=0
    return dict(tick=entry[0],wheels=ends,suspensions=susp,position=position,pitch=pitch,pitch_carry=0,centroid_carries=[0,0,0])
