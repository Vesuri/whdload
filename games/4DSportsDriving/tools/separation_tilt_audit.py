#!/usr/bin/env python3
"""Local angular sensitivity to captured separation vectors; not a new law."""
import hashlib,json,math
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tmp/prof'
def word(x):return (x+32768)%65536-32768
def pitch(v):
 y=word(v[2][1]+v[3][1]-v[0][1]-v[1][1])
 z=word(v[2][2]+v[3][2]-v[0][2]-v[1][2])
 return (math.atan2(word(-z),y)*512/math.pi-256+512)%1024-512
reports=[]
for contact,tilt in (('takeoff-early-contact50','takeoff-early-tilt50'),('penetration-course20','crest-entry-tilt20')):
 cp=P/contact/'penetration.json';tp=P/tilt/'tilt-baseline.json'
 contacts=json.loads(cp.read_text());t=json.loads(tp.read_text());assert contacts['rate']==t['rate']
 records=t['records'];final={r[0]:r for r in records['PITCH']}; observed=dict(records['PITCH_OUT'])
 pushes={}
 for r in contacts['rows']:
  if r['stage']=='PUSH_VECTOR' and r['tick'] in final:
   w=r['wheel'];assert w not in pushes.setdefault(r['tick'],{})
   pushes[r['tick']][w]=[r['correction_'+k] for k in ('x','y','z')]
 rows=[]
 for tick,bywheel in pushes.items():
  r=final[tick];assert r[1:10]==[16384,0,0,0,16384,0,0,0,16384], 'Only identity-heading captures supported'
  v=[r[10+i:13+i] for i in range(0,12,3)]
  # A common centroid translation cancels in rear-minus-front vectors. This
  # isolated sensitivity holds the remaining suspension and trajectory fixed.
  without=[[word(c-bywheel.get(w,[0,0,0])[i]) for i,c in enumerate(point)] for w,point in enumerate(v)]
  rows.append(dict(tick=tick,pushes=bywheel,final_pitch=pitch(v),observed_pitch=observed[tick],without_separation_pitch=pitch(without),separation_contribution=pitch(v)-pitch(without)))
 reports.append(dict(rate=t['rate'],contact_capture=contact,tilt_capture=tilt,contact_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),tilt_sha256=hashlib.sha256(tp.read_bytes()).hexdigest(),rows=rows))
report=dict(captures=reports,scope='Local geometric sensitivity at captured final pitch vectors, identity heading only. Removing separation here holds all other state fixed; it is neither a closed-loop simulation nor proof of an admissible runtime change. Native20 also rotates using separation; broad removal would change reference response. No world wheel, collision, velocity, or acceptance limit is modified.')
(P/'separation-tilt-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
