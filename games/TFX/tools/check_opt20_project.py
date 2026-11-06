"""Independent integer projection oracle and mismatch negative controls."""
import json,struct,sys,copy
from pathlib import Path
p=Path(sys.argv[1]);rows=json.loads((p/'results.json').read_text())
def model(c):
 out=bytearray()
 for x,y,z in c['points']:
  words=[0xa55a6996]*9;words[5:8]=[x&0xffffffff,y&0xffffffff,z];words[0:3]=[(v+t)&0xffffffff for v,t in zip(words[5:8],c.get("translation",[0,0,0]))]
  x,y,z=words[0:3];x=x-2**32 if x>=2**31 else x;y=y-2**32 if y>=2**31 else y
  depth=z>>16;depth=depth-65536 if depth&32768 else depth
  if depth<=16:words[3]=0xffff6996
  else:
   words[3]=0x6996;coords=[]
   for val,center in [(x,160),(y,100)]:
    val >>= c['shift'];q=abs(val)//depth*(-1 if val<0 else 1)
    coords.append((-32768 if q< -32768 else 32767 if q>32767 else q+center)&65535)
   words[4]=coords[0]*65536+coords[1]
  out += struct.pack('>9I',*words)
 return bytes(out)
def check(row):
 c=row['case'];a=bytes.fromhex(row['original']);b=bytes.fromhex(row['native']);m=model(c);n=len(m)
 skip={n+60+2+12+k*12+j for k in range(8) for j in [2,3]}
 return a[:n]==m and b[:n]==m and all(x==y or i in skip for i,(x,y) in enumerate(zip(a,b))) and len(a)==len(b)
assert all(check(x) for x in rows)
controls=[]
for index in [0,len(model(rows[0]['case'])),len(model(rows[0]['case']))+60,len(model(rows[0]['case']))+62]:
 bad=copy.deepcopy(rows[0]);raw=bytearray.fromhex(bad['native']);raw[index]^=1;bad['native']=raw.hex();assert not check(bad);controls.append(index)
report=dict(cases=len(rows),integer_oracle=True,full_register_and_fp_state=True,negative_controls=controls)
(p/'oracle.json').write_text(json.dumps(report,indent=2));print(report)
