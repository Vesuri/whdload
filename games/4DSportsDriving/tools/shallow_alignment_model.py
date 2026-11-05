"""Offline monotone same-face shallow-resting alignment.
Keep native wheel/suspension/centroid responses. Only when the uncompressed,
nonfalling car's proposed rotation crosses the selected plane's geometric angle,
stop rotation at that angle. Does not impose alignment on impacts or edge cases.
Plane angle is derived from its normal, never from a reference trajectory.
"""
from contact_body_predictor import body
from supported_plane_model import geometry
from airborne_pitch_predictor import atan_q8,wrap

def solve(entry,build,rows,state):
 out=body(entry,build,rows)
 eligible=(len({geometry(r)for r in rows})==1 and all(r['clearance']in(-1,0) and r['velocity']==r['velocity_fraction']==r['correction']==0 for r in rows) and not any(entry[13:21]) and any(r['clearance']==-1 for r in rows))
 if eligible:
  r=rows[0];assert r['normal_x']==0 and r['normal_y']>0
  target=wrap(atan_q8(r['normal_y'],r['normal_z'])-65536,18)
  before=entry[2]*256+entry[41];after=out['pitch']*256+out['pitch_carry']
  if (before-target)*(after-target)<0:
   pitch=(target+128)//256;out['pitch']=pitch;out['pitch_carry']=target-pitch*256
   out['alignment_limited']=dict(before=before,target=target,proposal=after)
 return out
