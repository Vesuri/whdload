exec(open(__file__.replace('measure_endpoint_ground_edges_c.py','test_endpoint_ground_c.py')).read().split('resets=notifications=0')[0])
import itertools,json
results=[];violations=[];contacts=0
for rate,x,y,heading,speed in itertools.product([50,60],[0x1800,0x1801,0xd7ff,0xd800],[0x1800,0xd800],[0,64,128,192],[-96,96]):
 span=17 if rate==50 else 20
 b=bytearray(86);struct.pack_into('>HH',b,0,x,y);struct.pack_into('>H',b,28,2);struct.pack_into('>h',b,42,speed)
 b[16]=2;b[27]=128;b[53]=heading;b[61]=heading;b[54]=244;b[55]=16;b[57]=26;b[62]=228;b[66]=28;b[80]=(speed>>2)&255
 c.put(p,b);c.put(event,bytes(4));assert call('endpoint_player_init',{1:owner,9:rate,10:0})==0;assert call('endpoint_player_begin',{1:owner,2:p,9:span,10:1})==0
 for f in range(1,span+1):
  direction=1 if f<=span//2 else -1;c.put(packet,struct.pack('>hhhhh',direction,-direction,0,0,0))
  assert call('endpoint_player_step',{1:owner,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:f})==0
 before=c.get(p,86);result=call('endpoint_ground_resolve',{1:owner,2:p,3:stages,4:ground,5:event});assert result in [0,1]
 xy=struct.unpack('>HH',c.get(p,4));fractions=struct.unpack('>II',c.get(owner,8));contacts+=result
 record=dict(rate=rate,start=[x,y],heading=heading,speed=speed,contact=result,before=list(struct.unpack('>HH',before[:4])),after=list(xy),fractions=list(fractions))
 results.append(record)
 if result and (any(not 0x1800<=v<=0xd800 for v in xy) or any(v==0xd800 and r for v,r in zip(xy,fractions))):violations.append(record)
(root/'tmp/c/endpoint-ground-edges.json').write_text(json.dumps(dict(cases=len(results),contacts=contacts,violations=violations,results=results),indent=2)+'\n')
print(dict(cases=len(results),contacts=contacts,violations=len(violations),examples=violations[:3]));c.close()
