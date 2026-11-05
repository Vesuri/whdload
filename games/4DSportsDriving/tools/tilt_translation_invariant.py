#!/usr/bin/env python3
"""Audit 50Hz tilt under pure translation, including suspension restoration.
This is an invariant diagnostic, not a course handling acceptance test.
"""
from pathlib import Path
import json
from native_contact_response import sine,rotate,atan_native
from contact_body_predictor import tilt
from airborne_pitch_predictor import axis
extensions=[(0,0,0,0),(384,384,384,384),(-384,-384,-384,-384),(384,384,-384,-384),(-384,-384,384,384),(137,137,-83,-83)]
cases=0;fail=[];native_bias=[]
for pitch in range(-255,256):
 for ex in extensions:
  sn,cs=sine(pitch),sine(pitch+256);m=[16384,0,0,0,cs,-sn,0,sn,cs];old=[]
  for w,(x,z)in enumerate(((-960,1984),(960,1984),(960,-1984),(-960,-1984))):
   p=rotate([x,-384-ex[w],z],m);lift=rotate([0,384+ex[w],0],m);old.append([a+b for a,b in zip(p,lift)])
  final=[[x+777,y-313,z+1543]for x,y,z in old]
  native=atan_native(*axis(old))-256
  if native!=pitch:native_bias.append(dict(pitch=pitch,extension=ex,reconstructed=native))
  for carry in (-128,-1,0,1,127):
   got=tilt(old,final,carry);cases+=1
   # Native near-level dead zone is intentionally retained; inspect separately.
   if abs(2*(pitch*256+carry))>=816 and got!=(pitch,carry):fail.append(dict(pitch=pitch,extension=ex,carry=carry,result=got,native_baseline=native))
report=dict(scope=__doc__,cases=cases,native_baseline_mismatches=native_bias,non_deadzone_translation_changes=fail,deadzone_rule='abs(2*(pitch*256+carry))<816 for zero geometric delta')
Path('tmp/prof/tilt-translation-invariant.json').write_text(json.dumps(report,indent=2)+'\n')
print('cases',cases,'native baseline mismatches',len(native_bias),'non-deadzone changes',len(fail));print(fail[:8])
