exec(open(__file__.replace('test_endpoint_ground_edge_regression_c.py','test_endpoint_ground_c.py')).read().split('resets=notifications=0')[0])
import json
example=json.loads((root/'tmp/c/endpoint-ground-edge-failure.json').read_text())['found'][0]
for rate,span in [(50,17),(60,20)]:
 b=bytes.fromhex(example['initial']);c.put(p,b);c.put(event,bytes(4));assert call('endpoint_player_init',{1:owner,9:rate,10:0})==0;assert call('endpoint_player_begin',{1:owner,2:p,9:span,10:1})==0
 for f in range(1,span+1):
  x,y=example['controls'][0 if f<=span//2 else 1];c.put(packet,struct.pack('>hhhhh',x,y,0,0,0));assert call('endpoint_player_step',{1:owner,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:f})==0
 if rate==50:assert c.get(p,86).hex()==example['before']
 assert call('endpoint_ground_resolve',{1:owner,2:p,3:stages,4:ground,5:event})==1
 assert struct.unpack('>HH',c.get(p,4))==(0xd800,0x1800)
 assert c.get(owner,8)==bytes(8)
print(dict(reproduced_changed_input_landings=2,coordinates_clamped=True,outward_debt_cleared=True));c.close()
