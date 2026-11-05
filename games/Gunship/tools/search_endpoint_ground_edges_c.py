exec(open(__file__.replace('search_endpoint_ground_edges_c.py','test_endpoint_ground_c.py')).read().split('resets=notifications=0')[0])
import random,math,json
from fractions import Fraction as F
rng2=random.Random(0x1800);spec=[(0,2,0,1),(2,2,0,1),(28,2,0,0),(42,2,1,0),(27,1,0,0),(53,1,0,1),(61,1,0,1),(54,1,1,0),(55,1,1,0),(62,1,1,0)]
read=lambda b,o,n,s:int.from_bytes(b[o:o+n],'big',signed=bool(s))
found=[];contacts=0
for trial in range(2048):
 b=bytearray(86);struct.pack_into('>HH',b,0,rng2.choice([0x1800,0x1801,0xd7ff,0xd800]),rng2.choice([0x1800,0x8000,0xd800]));struct.pack_into('>H',b,28,2);speed=rng2.randrange(-128,257);struct.pack_into('>h',b,42,speed)
 b[16]=rng2.choice([0,2]);b[27]=128;b[53]=b[61]=rng2.randrange(256);b[54]=rng2.randrange(-12,21)&255;b[55]=rng2.randrange(-20,21)&255;b[57]=rng2.randrange(43);b[62]=228;b[66]=28;b[80]=(speed>>2)&255
 controls=[(rng2.choice([-1,0,1]),rng2.choice([-1,0,1])) for _ in range(2)];targets=[]
 for x,y in controls:
  c.put(out,b);c.put(packet,struct.pack('>hhhhh',x,y,0,0,0));assert call('player_step_init',{1:shadow,9:3,10:0})==0;assert call('player_step_interval',{1:shadow,2:out,3:stages,4:h[0]+0x7a44,5:packet,9:1})==0;targets.append(c.get(out,86))
 final=bytearray(targets[-1]);res=[]
 for o,n,s,circular in spec:
  anchor=read(b,o,n,s);deltas=[read(t,o,n,s)-anchor for t in targets];mod=1<<(8*n)
  if circular:deltas=[(d+mod//2)%mod-mod//2 for d in deltas]
  value=F(anchor)+F(deltas[0]*8+deltas[1]*9,17);whole=math.floor(value);res.append(int((value-whole)*1360));final[o:o+n]=(whole%mod).to_bytes(n,'big')
 c.put(p,b);c.put(event,bytes(4));assert call('endpoint_player_init',{1:owner,9:50,10:0})==0;assert call('endpoint_player_begin',{1:owner,2:p,9:17,10:1})==0
 c.put(p,final);c.put(owner,struct.pack('>10I',*res));c.put(owner+160,struct.pack('>H',17))
 result=call('endpoint_ground_resolve',{1:owner,2:p,3:stages,4:ground,5:event});assert result in [0,1];contacts+=result
 xy=struct.unpack('>HH',c.get(p,4));fr=struct.unpack('>II',c.get(owner,8))
 invalid=result and any(v<0x1800 or v>0xd800 or (v==0xd800 and r) for v,r in zip(xy,fr))
 if invalid:
  # Confirm the constructed interval with all actual assembled field steps.
  c.put(p,b);c.put(event,bytes(4));assert call('endpoint_player_init',{1:owner,9:50,10:0})==0;assert call('endpoint_player_begin',{1:owner,2:p,9:17,10:1})==0
  for f in range(1,18):
   x,y=controls[0 if f<=8 else 1];c.put(packet,struct.pack('>hhhhh',x,y,0,0,0));assert call('endpoint_player_step',{1:owner,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:f})==0
  assert c.get(p,86)==final and c.get(owner,40)==struct.pack('>10I',*res)
  assert call('endpoint_ground_resolve',{1:owner,2:p,3:stages,4:ground,5:event})==1
  assert xy==struct.unpack('>HH',c.get(p,4)) and fr==struct.unpack('>II',c.get(owner,8))
  found.append(dict(trial=trial,initial=b.hex(),controls=controls,before=final.hex(),xy=xy,fractions=fr));break
(root/'tmp/c/endpoint-ground-edge-search.json').write_text(json.dumps(dict(trials=trial+1,contacts=contacts,found=found),indent=2)+'\n')
print(dict(trials=trial+1,contacts=contacts,found=found));c.close()
