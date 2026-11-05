#!/usr/bin/env python3
"""Compare raw-wheel and suspension-restored body heading baselines."""
import json,math,sys
from pathlib import Path
cap=Path(sys.argv[1]);data=json.loads((cap/'tilt-baseline.json').read_text());root=Path(__file__).resolve().parents[1]
raw=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes();at=0x3a1dc+0x7ffe;table=raw[at-0x386c:at-0x386c+257]
def word(v):return (v+32768)%65536-32768
def wrap(v):return (v+512)%1024-512
def native(x,y):
 assert abs(x)<32768 and abs(y)<32768
 o=(4 if x<0 else 0)+(2 if y<0 else 0);x,y=abs(x),abs(y)
 if x==y:
  if not x:return 0
  angle=128
 else:
  if x>y:x,y=y,x;o+=1
  q=(x<<16)//y;angle=table[(q>>8)+((q>>7)&1)]
 return (angle,256-angle,512-angle,256+angle,-angle,angle-256,angle-512,-256-angle)[o]
def vector(v):return (word(v[2][0]+v[3][0]-v[0][0]-v[1][0]),word(-(v[2][2]+v[3][2]-v[0][2]-v[1][2])))
def angle(v):return math.atan2(*v)*512/math.pi
rows=[]
for b,y,out in zip(*(data['records'][k] for k in ('BUILT','YAW','YAW_OUT'))):
 assert b[0]==y[0]==out[0]
 m=b[9:18];old=[b[18+i:21+i] for i in range(0,12,3)]
 body=[[v[i]+word((e+384)*m[3+i]//16384) for i in range(3)] for v,e in zip(old,b[5:9])]
 ov,bv=vector(old),vector(body);oa,ba=angle(ov),angle(bv)
 rows.append(dict(tick=b[0],old_heading=wrap(b[2]),new_heading=wrap(out[1]),spin=b[31],
                  raw_vector=ov,body_vector=bv,raw_native=native(*ov),body_native=native(*bv),
                  raw_native_bias=wrap(native(*ov)-b[2]),body_native_bias=wrap(native(*bv)-b[2]),
                  raw_rounding=wrap(native(*ov)-oa),body_rounding=wrap(native(*bv)-ba),
                  final_exact=angle((y[1],word(-y[2])))))
summary={k:sum(r[k] for r in rows) for k in ('raw_native_bias','body_native_bias','raw_rounding','body_rounding')}
summary['native_baseline_differences']=sum(r['raw_native']!=r['body_native'] for r in rows)
summary['calls']=len(rows)
(cap/'yaw-basis-check.json').write_text(json.dumps(dict(summary=summary,rows=rows,scope='Observed geometry only; sums are not a prediction of changed closed-loop motion.'),indent=2)+'\n')
print(json.dumps(summary,indent=2))
for r in rows:
 if r['raw_native']!=r['body_native']:print(json.dumps(r))
