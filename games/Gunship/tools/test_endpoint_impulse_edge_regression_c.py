exec(open(__file__.replace('test_endpoint_impulse_edge_regression_c.py','test_endpoint_ground_c.py')).read().split('resets=notifications=0')[0])
import json
ex=json.loads((root/'tmp/c/endpoint-impulse-edge-failure.json').read_text())['found'][0]
for rate,span in [(50,17),(60,20)]:
 b=bytes.fromhex(ex['initial']);c.put(p,b);assert call('endpoint_player_init',{1:owner,9:rate,10:0})==0;assert call('endpoint_player_begin',{1:owner,2:p,9:span,10:1})==0
 for f in range(1,span+1):
  x,y=ex['controls'][0 if f<=span//2 else 1];c.put(packet,struct.pack('>hhhhh',x,y,*(ex['impulses'] if f==span else (0,0,0))));assert call('endpoint_player_step',{1:owner,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:f})==0
 assert struct.unpack('>HH',c.get(p,4))==(0x1807,0xd807)
 assert c.get(owner,8)==bytes(8)
cases=0
for rate,span in [(3,1),(50,17),(60,20)]:
 for wind in [-128,-8,0,7,127]:
  b=bytearray.fromhex(ex['initial']);b[20]=b[21]=wind&255
  c.put(out,b);c.put(packet,struct.pack('>hhhhh',1,-1,*ex['impulses']));assert call('player_step_init',{1:shadow,9:3,10:0})==0
  assert call('player_step_interval',{1:shadow,2:out,3:stages,4:h[0]+0x7a44,5:packet,9:1})==0;expected=c.get(out,86)
  c.put(p,b);assert call('endpoint_player_init',{1:owner,9:rate,10:0})==0;assert call('endpoint_player_begin',{1:owner,2:p,9:span,10:1})==0
  for f in range(1,span+1):
   c.put(packet,struct.pack('>hhhhh',1,-1,*(ex['impulses'] if f==span else (0,0,0))));assert call('endpoint_player_step',{1:owner,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:f})==0
  assert c.get(p,86)==expected,(rate,wind);cases+=1
print(dict(changed_input_regressions=2,native_wind_endpoints=cases));c.close()
