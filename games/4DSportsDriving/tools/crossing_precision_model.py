"""Offline crossing-distance precision screen, retaining native decisions.

Only native crossing branches receive a finer matrix-local intersection.
Force activation, suspension, total movement budget, tangent and residual push
retain current semantics. Unsupported sign/budget cases are explicit failures.
"""
from fractions import Fraction as F
from unittest.mock import patch
import contact_body_predictor as model
from native_contact_response import resolve as native,rotate,word,plane,length3,trunc,UnsupportedContact

def resolve(old,new,geo,distance,down,velocity,flags=0):
 out=native(old,new,geo,distance,down,velocity,flags)
 if out['branch']!='crossing':return out
 m=[geo['matrix'+str(i)]for i in range(9)];origin=[64*geo['origin_'+a]for a in 'xyz']
 def local(v):
  p=[v[i]-origin[i]for i in range(3)]
  q=[F(sum(p[j]*m[3*i+j]for j in range(3)),16384)for i in range(3)]
  return [q[0],q[2],-q[1]]
 ov,nv=local(old),local(new);den=nv[2]-ov[2]
 if den<=0:raise UnsupportedContact('Fine crossing denominator is not positive')
 fraction=-ov[2]/den
 if not 0<=fraction<=1:raise UnsupportedContact('Native crossing does not cross the fine matrix plane')
 intersection=[ov[i]+(nv[i]-ov[i])*fraction for i in (0,1)]+[F(0)]
 vector=[word(trunc((y-x).numerator,(y-x).denominator))for x,y in zip(intersection,nv)]
 projected=length3(vector);total=word(distance+down);rest=word(total-projected)
 if total<=0 or not 0<=rest<=total:raise UnsupportedContact('Fine crossing has nonphysical native span ratio')
 straight=[word(trunc((b-a)*rest,total))for a,b in zip(old,new)]
 tangent=rotate([0,0,projected],m);candidate=[a+b+c for a,b,c in zip(old,straight,tangent)];residual=plane(geo,candidate)
 push=rotate([0,word(-residual*64),0],m)if residual<0 else[0,0,0]
 out.update(position=[a+b for a,b in zip(candidate,push)],stored_clearance=residual,fine_fraction=str(fraction),native_projected=out['projected_distance'],projected_distance=projected,before_push=candidate,push=push,straight=straight,tangent=tangent,intersection=[str(x)for x in intersection],rest=rest,total=total,recomputed_clearance=plane(geo,[a+b for a,b in zip(candidate,push)]))
 return out

def solve(entry,build,rows,state):
 with patch.object(model,'resolve',resolve):return model.body(entry,build,rows)
def control(entry,build,rows,state):
 with patch.object(model,'resolve',native):return model.body(entry,build,rows)
