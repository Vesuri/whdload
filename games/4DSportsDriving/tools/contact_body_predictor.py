"""Native-compatible straight contact/suspension/body predictor, supplied planes."""
from native_contact_response import plane,resolve,rotate,word,atan_native,UnsupportedContact
from airborne_pitch_predictor import atan_q8,axis,wrap
def trunc(n,d):return abs(n)//d*(1 if n>=0 else -1)
def suspension(extension,bias,clearance,ef,bf):
    old=extension
    if bias:
        n=(8 if bias<0 else -8)+bf;step=trunc(n,5);bf=n-step*5
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
        n=2*min(c,192)+ef;step=trunc(n,5);ef=n-step*5
        extension=word(extension+step)
        if extension>=384:extension=384;ef=0
    else:
        if word(extension+c)>-288:extension=word(extension+c)
        else:extension=max(-384,word(extension+(word(c*3)>>2)))
        adjustment=word(word(old-extension)+c)
    return dict(returned=word(old+adjustment),extension=extension,bias=bias,ef=ef,bf=bf,branch_clearance=c)
def wheel(r):
    if r['correction']!=0:raise UnsupportedContact('Roof correction domain not supported')
    old=[r['old_world_'+a] for a in 'xyz'];new=[r['world_'+a] for a in 'xyz']
    geo={k:r[k] for k in ('plane','plane_flags','normal_x','normal_y','normal_z',*('matrix'+str(i) for i in range(9)))}
    geo.update({'origin_'+a:word(r['base_'+a]+r['node_'+a]) for a in 'xyz'})
    q=plane(geo,new);assert q==r['clearance']
    v=r['velocity'];vf=r['velocity_fraction'];pf=r['position_fraction'];ef=r['extension_fraction']
    applied=q>0;down=0
    if applied:
        a=21 if r['wheel']<2 else 15
        down,pf=divmod(10*v+2*vf+7*a+pf,25)
        dv,vf=divmod(2*a+vf,5);v=word(v+dv);new[1]-=down
        q=plane(geo,new)
    suspension_clearance=q
    if q<0:
        ratio=down if applied else trunc(10*v+2*vf,25)
        out=resolve(old,new,geo,r['distance'],ratio,v,r['impact_flags'])
        new=out['position'];q=out['stored_clearance'];branch=out['branch']
    else:branch='zero' if q==0 else 'air'
    if branch!='air':v=vf=pf=ef=0
    return dict(position=new,clearance=q,suspension_clearance=suspension_clearance,velocity=v,vf=vf,pf=pf,ef=ef,branch=branch,applied_gravity=applied,down=down)
def tilt(old,final,carry):
    a=axis(old);b=axis(final)
    if a==(0,0) or b==(0,0):raise UnsupportedContact('Degenerate body axis')
    baseline=atan_native(*a)*256;delta=wrap(atan_q8(*b)-atan_q8(*a),18)
    base=baseline-65536+carry
    reference=wrap(2*base+5*delta,19);actual=wrap(2*base+2*delta,19)
    if max(abs(reference),abs(actual))<816:return 0,0
    q=baseline+delta+carry+128;carry=q%256-128;angle=(q>>8)&1023
    if angle>512 or angle==512 and b[0]<0:angle-=1024
    return angle-256,carry
def body(entry,build,selected,wheel_solver=wheel):
    assert len(entry)==69
    tick,heading,pitch,roll=entry[:4]
    if heading or roll:raise UnsupportedContact('Straight zero-heading/roll domain required')
    m=entry[4:13];ext=entry[13:17];bias=entry[17:21];bfs=entry[37:41];carry=entry[41];cc=entry[42:45]
    old=[entry[45+3*w:48+3*w] for w in range(4)]
    translated=[entry[57+3*w:60+3*w] for w in range(4)]
    ends=[];returns=[];start_basis=[];final_basis=[];remainder=[0,0,0]
    for w in range(4):
        r=selected[w];assert r['tick']==tick and r['wheel']==w
        assert [r['old_world_'+a] for a in 'xyz']==old[w]
        assert [r['world_'+a] for a in 'xyz']==translated[w]
        for key,offset in (('extension',13),('velocity',21),('velocity_fraction',25),('position_fraction',29),('extension_fraction',33)):
            assert r[key]==entry[offset+w],(tick,w,key,r[key],entry[offset+w])
        out=wheel_solver(r);ends.append(out)
        s=suspension(ext[w],bias[w],out['suspension_clearance'],out['ef'],bfs[w]);returns.append(s)
        restore=rotate([0,384+ext[w],0],m)
        start_basis.append([x+y for x,y in zip(old[w],restore)])
        lift=[0,384+s['returned'],0]
        final_basis.append([x+y for x,y in zip(out['position'],rotate(lift,m))])
        for v in (build[w],lift):
            for i in range(3):remainder[i]+=sum(v[j]*m[3*j+i] for j in range(3))%16384
    new_pitch,newcarry=tilt(start_basis,final_basis,carry)
    positions=[];carries=[]
    for i in range(3):
        p,c=divmod(sum(v[i] for v in final_basis)*16384+remainder[i]+cc[i],65536)
        positions.append(p);carries.append(c)
    return dict(tick=tick,wheels=ends,suspensions=returns,position=positions,centroid_carries=carries,pitch=new_pitch,pitch_carry=newcarry)
