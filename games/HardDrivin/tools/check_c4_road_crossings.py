"""Geometric diagnosis only: car-center segments against loop road triangles."""
from pathlib import Path
import json,math
root=Path('tmp/prof');g=json.loads(Path('tmp/track-geometry.json').read_text())['stunt']
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def hit(p,q,a,b,c):
 d=sub(q,p);e1=sub(b,a);e2=sub(c,a);h=cross(d,e2);det=dot(e1,h)
 if abs(det)<1e-9:return
 f=1/det;s=sub(p,a);u=f*dot(s,h)
 if not 0<=u<=1:return
 k=cross(s,e1);v=f*dot(d,k)
 if v<0 or u+v>1:return
 t=f*dot(e2,k)
 if 1e-6<t<1-1e-6:return t
runs={}
for name in ['c4-loop-follow-native-v3','c4-loop-terrain-slow','c4-road-pitch-loop-slow-v3','c4-road-gain-loop-slow','c4-road-gain-loop-060']:
 rows=[r for r in json.loads((root/name/'motion.json').read_text())['rows'] if r['kind']=='STEP'];events=[]
 for r,s in zip(rows,rows[1:]):
  p=[r[k]/8 for k in ['x8','y8','z8']];q=[s[k]/8 for k in ['x8','y8','z8']]
  for i in range(37,49):
   a,b,c,d=g[i]['left'],g[i]['right'],g[i+1]['right'],g[i+1]['left']
   for triangle in [(a,b,c),(a,c,d)]:
    t=hit(p,q,*triangle)
    if t is not None:events.append(dict(previous_field=r['field'],field=s['field'],segment=i,fraction=t,previous_mask=r['mask'],mask=s['mask'],previous_pitch=r.get('pitch'),pitch=s.get('pitch')))
 first=next((r for r in rows if r['mask']==0),None)
 runs[name]=dict(first_air=None if first is None else {k:first.get(k) for k in ['field','consumed','pitch','mask','crash']},road_crossings=events,checkpoint_changes=len(set(r.get('course_next') for r in rows))-1,last={k:rows[-1].get(k) for k in ['field','pitch','mask','crash','checkpoint_latch']})
report=dict(passed=False,scope='Private road-angle fallback and scaled response remain rejected. Car-center straight segments between post-contact samples intersect triangulated road quads; these are geometric diagnostics, not swept wheel proofs or proof of missing native collision checks. Curved trajectory and contact corrections are not reconstructed.',runs=runs)
Path('tmp/c4-road-pitch-experiment.json').write_text(json.dumps(report,indent=2)+'\n')
for n,r in runs.items():print(n,'firstair',r['first_air'],'crossings',len(r['road_crossings']),'nearfirstair',[e for e in r['road_crossings'] if r['first_air'] and abs(e['field']-r['first_air']['field'])<30],'last',r['last'])
