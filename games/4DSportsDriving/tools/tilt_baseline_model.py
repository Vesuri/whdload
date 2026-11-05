#!/usr/bin/env python3
"""Analyze suspension-restored old wheel geometry in the live Euler frames."""
import json,math,sys
from pathlib import Path
cap=Path(sys.argv[1]);r=json.loads((cap/'tilt-baseline.json').read_text());rows=[]
def word(v):return (v+32768)%65536-32768
def wrap(v):return (v+512)%1024-512
def rotate(v,m):return [word(sum(v[j]*m[3*j+i] for j in range(3))//16384) for i in range(3)]
def triples(v):return [v[i:i+3] for i in range(0,len(v),3)]
def pitch(v):
 d=[word(v[2][i]+v[3][i]-v[0][i]-v[1][i]) for i in range(3)]
 return wrap(math.atan2(word(-d[2]),d[1])*512/math.pi-256)
def roll(v):
 d=[word(v[1][i]+v[2][i]-v[0][i]-v[3][i]) for i in range(3)]
 return wrap(math.atan2(d[0],d[1])*512/math.pi-256)
for built,pr,po,rr,ro in zip(*(r['records'][k] for k in ('BUILT','PITCH','PITCH_OUT','ROLL','ROLL_OUT'))):
 tick=built[0];assert all(v[0]==tick for v in (pr,po,rr,ro))
 old_angles=built[2:5];extension=built[5:9];matrix=built[9:18];old=triples(built[18:30])
 corrected=[]
 for v,e in zip(old,extension):
  correction=rotate([0,e+384,0],matrix)
  corrected.append([a+b for a,b in zip(v,correction)])
 center=[sum(v[i] for v in corrected)//4 for i in range(3)]
 relative=[[word(v[i]-center[i]) for i in range(3)] for v in corrected]
 yaw=pr[1:10];base_pitch=[rotate(v,yaw) for v in relative];final_pitch=triples(pr[10:22])
 base_roll=[rotate(v,rr[1:10]) for v in base_pitch] if po[1] else base_pitch
 final_roll=triples(rr[10:22])
 rows.append(dict(tick=tick,old_pitch=old_angles[1],old_roll=old_angles[2],spin=built[31],
                  baseline_pitch=pitch(base_pitch),final_pitch_exact=pitch(final_pitch),final_pitch_native=po[1],
                  pitch_change=wrap(pitch(final_pitch)-pitch(base_pitch)),
                  baseline_roll=roll(base_roll),final_roll_exact=roll(final_roll),final_roll_native=ro[1],
                  roll_change=wrap(roll(final_roll)-roll(base_roll))))
result=dict(rate=r['rate'],rows=rows,scope='Bias model restores INITIAL suspension extension before centering and applying the same final heading/pitch matrices. Not a corrected closed-loop simulation.')
(cap/'tilt-baseline-model.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:
 if row['tick']%5==0:print(json.dumps(row))
