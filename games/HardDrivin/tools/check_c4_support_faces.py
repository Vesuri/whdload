"""Independent finite-face support oracle for the saved jump surface candidates."""
from pathlib import Path
from fractions import Fraction
import json
raw=json.loads(Path('tmp/c4-jump-plane-replay.json').read_text())
def support(vertices,x,z):
 # Convex footprint and upward car-space normal. Reject zero-area projections.
 signs=[]
 for a,b in zip(vertices,vertices[1:]+vertices[:1]):
  cross=(b[0]-a[0])*(z-a[2])-(b[2]-a[2])*(x-a[0])
  if cross:signs.append(1 if cross>0 else -1)
 if not signs or min(signs)!=max(signs):return None
 a,b,c=vertices[:3];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
 nx=u[1]*v[2]-u[2]*v[1];ny=u[2]*v[0]-u[0]*v[2];nz=u[0]*v[1]-u[1]*v[0]
 if ny<=0:return None
 return Fraction(a[1])-Fraction(nx*(x-a[0])+nz*(z-a[2]),ny)
faces=raw['unclipped_object_faces'];points=[(0,0),(-30,45),(30,45),(-30,-45),(30,-45)]
answers=[]
for face in faces:
 answers.append(dict(index=face['index'],normal=face['normal'],support=[str(y) if (y:=support(face['vertices'],x,z)) is not None else None for x,z in points]))
assert [a['index'] for a in answers if a['support'][0] is not None]==[3]
# Winding controls which side supports; translating query and vertices preserves results.
cases=0
for face in faces:
 for x,z in points:
  original=support(face['vertices'],x,z)
  for dx,dy,dz in [(0,0,0),(400,-71,-233),(-1000,200,1200)]:
   shifted=[[v[0]+dx,v[1]+dy,v[2]+dz] for v in face['vertices']]
   assert support(shifted,x+dx,z+dz)==(None if original is None else original+dy)
   cases+=1
report=dict(passed=True,cases=cases,query_points=points,faces=answers,scope='Exact rational finite convex-face oracle in recorded car coordinates. Proves which saved object faces cover the chosen query points, not runtime behavior, whole model coverage, world-up classification, collision response or cost.')
Path('tmp/c4-support-faces-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
