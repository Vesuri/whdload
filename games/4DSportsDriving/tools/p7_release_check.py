from p7_screen import wheel,OUT
from fractions import Fraction as F
import json
results=[]
for start,w,expected in ((560,0,189),(564,2,105)):
 r=dict(wheel=w,correction=0,plane=0,plane_flags=1,normal_x=0,normal_y=8192,normal_z=0,base_x=0,base_y=0,base_z=0,node_x=0,node_y=0,node_z=0,velocity=0,velocity_fraction=0,position_fraction=0,extension_fraction=0,distance=0,impact_flags=0)
 r.update({'matrix'+str(i):v for i,v in enumerate([16384,0,0,0,16384,0,0,0,16384])})
 records=[]
 for n in range(start,581):
  r.update(tick=n,clearance=100000>>6,old_world_x=0,old_world_y=100000,old_world_z=0,world_x=0,world_y=100000,world_z=0)
  out=wheel(r)
  r.update(velocity=out['velocity'],velocity_fraction=out['vf'],position_fraction=out['pf'])
  records.append(dict(tick=n,velocity=out['velocity'],vf=out['vf'],down=out['down'],pf=out['pf']))
 assert F(out['velocity'])+F(out['vf'],5)==expected
 results.append(dict(first_tick=start,wheel=w,expected=expected,records=records))
# For linearly changing calibrated distance Q, h=2/5. The endpoint correction
# is (1-h)/2 * deltaQ = 3/10 * deltaQ, derived from native v+=a;x+=v.
h=F(2,5)
assert sum(h*(i*h)+F(3,10)*h for i in range(1,6))==3 # two native steps: 1+2
(OUT/'release-and-distance-derivation.json').write_text(json.dumps(dict(release=results,distance='h*Qnew + (1-h)/2*(Qnew-Qold), h=2/5; extra remainder denominator10. Constant-Q existing fifths unchanged; five constant-acceleration updates sum to two native updates.'),indent=2)+'\n')
print('First-release controls: front189/rear105; native constant-acceleration two/five identity exact')
