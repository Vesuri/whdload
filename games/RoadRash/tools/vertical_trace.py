import sys,json,struct
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s);s.input('JOY2_UP',1);s.cmd('break *0x875f2')
 for i in range(2200):
  s.cmd('continue',timeout=60)
  b=read_bytes(s,0xa5d00,0xe0);w=lambda o:struct.unpack_from('>h',b,o)[0];l=lambda o:struct.unpack_from('>I',b,o)[0]
  camera=l(0x1e);idx=camera>>16;track=read_bytes(s,0xa851a+2*(idx&255),2)
  row=dict(field=l(0x4c),camera=camera,segment=idx,fraction=camera&65535,slope=struct.unpack('>bb',track),camera_height=l(0x1a),road_base=w(0xc),road_fraction=w(0x10),world_height=w(0x62),air_height=w(0x92),height_base=w(0x9a),height_fraction=w(0x9c),pos=l(0x64),flags=b[0xc8],crash=b[0xce])
  rows.append(row)
  if i%250==0:print(i,row,flush=True)
 (s.out/'trace.json').write_text(json.dumps(rows,indent=2))
finally:s.quit()
