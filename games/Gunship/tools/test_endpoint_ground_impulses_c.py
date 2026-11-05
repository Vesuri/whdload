exec(open(__file__.replace('test_endpoint_ground_impulses_c.py','test_endpoint_ground_c.py')).read().split('resets=notifications=0')[0])
import itertools
cases=fields=resets=0
for rate,height,speed,engine,config in itertools.product([50,60],[0,1,3,32767],[0,8,96,-16],[0,28],[0,2]):
 span=20 if rate==60 else [17,16][cases%2]
 b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,height);struct.pack_into('>h',b,42,speed)
 b[16]=config;b[27]=128;b[54]=[-12,0,20][cases%3]&255;b[55]=9;b[57]=30;b[62]=236;b[63]=2;b[66]=engine;b[80]=(speed>>2)&255
 impulses=([-4,0,4][cases%3],[-1,0,1][cases%3],[-2,-1,0,1,2][cases%5] if height else 0)
 c.put(out,b);c.put(event,bytes(4));c.put(packet,struct.pack('>hhhhh',0,0,*impulses));c.put(binding,struct.pack('>II',ground,event))
 assert call('player_step_init',{1:shadow,9:3,10:0})==0
 assert call('endpoint_ground_preview',{1:shadow,2:out,3:stages,4:h[0]+0x7a44,5:packet,7:binding,9:1})==0
 expected=c.get(out,86),c.get(event,4)
 c.put(p,b);c.put(event,bytes(4));assert call('endpoint_player_init',{1:owner,9:rate,10:0})==0
 assert call('endpoint_player_begin',{1:owner,2:p,9:span,10:1})==0
 for f in range(1,span+1):
  c.put(packet,struct.pack('>hhhhh',0,0,*(impulses if f==span else (0,0,0))))
  assert call('endpoint_player_step',{1:owner,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:f})==0
  assert c.get(event,4)==bytes(4);fields+=1
 result=call('endpoint_ground_resolve',{1:owner,2:p,3:stages,4:ground,5:event});assert result in [0,1];resets+=result
 assert expected==(c.get(p,86),c.get(event,4)),(rate,height,speed,engine,config,[(i,x,y) for i,(x,y) in enumerate(zip(expected[0],c.get(p,86))) if x!=y])
 cases+=1
# Contact discards only reset quantities' fractional debt.
c.put(event,bytes(4));c.put(p+28,bytes(2));c.put(owner,struct.pack('>10I',*([777]*10)))
assert call('endpoint_ground_resolve',{1:owner,2:p,3:stages,4:ground,5:event})==1
assert list(struct.unpack('>10I',c.get(owner,40)))==[777,777,0,0,777,777,777,0,0,0]
# Incomplete interval and malformed residue reject without any writes.
for kind in ['phase','residue']:
 c.put(event,bytes(4));c.put(owner+160,c.get(owner+158,2))
 if kind=='phase':c.put(owner+160,bytes(2))
 else:c.put(owner+36,struct.pack('>I',1360))
 before=c.get(p,86),c.get(owner,164),c.get(event,4)
 assert call('endpoint_ground_resolve',{1:owner,2:p,3:stages,4:ground,5:event})==0xffffffff
 assert before==(c.get(p,86),c.get(owner,164),c.get(event,4))
print(dict(cases=cases,fields=fields,ground_resets=resets,native_endpoints_match=True,fraction_reset=True,rejections_atomic=True,calls=calls))
c.close()
