from pathlib import Path
exec(Path(__file__).with_name('test_pitch_control_clamp_c.py').read_text().split('cases=0')[0])
for rate,y,previous,remainder in [(49,0,0,0),(50,2,0,0),(50,0,2,0),(50,0,0,50),(60,0,0,-60)]:
 c.put(state,struct.pack('>Hhii',rate,previous,0,remainder));c.put(p,bytes(86));c.put(p+54,b'\x7f');c.put(packet,struct.pack('>hhhhh',0,y,0,0,0))
 before=c.get(state,12),c.get(p,86)
 assert call('attitude_pitch_clamp_control',{1:state,2:p,3:packet})==0xffffffff
 assert before==(c.get(state,12),c.get(p,86))
print('Five invalid clamp inputs rejected without writes.')
