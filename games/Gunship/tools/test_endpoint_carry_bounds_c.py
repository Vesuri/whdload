exec(open(__file__.replace('test_endpoint_carry_bounds_c.py','test_endpoint_ground_c.py')).read().split('resets=notifications=0')[0])
b=bytearray(86);struct.pack_into('>HH',b,0,0x8000,0x8000);struct.pack_into('>H',b,28,1024);b[27]=128;b[55]=16;b[57]=26;b[66]=28
c.put(p,b);assert call('endpoint_player_init',{1:owner,9:50,10:0})==0
rolls=[]
for tick in [1,2]:
 assert call('endpoint_player_begin',{1:owner,2:p,9:17,10:tick})==0
 for f in range(1,18):
  x=1 if tick==2 or f<=8 else 0;c.put(packet,struct.pack('>hhhhh',x,0,0,0,0));assert call('endpoint_player_step',{1:owner,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:(tick-1)*17+f})==0
 rolls.append((int.from_bytes(c.get(p+55,1),'big',signed=True),int.from_bytes(c.get(owner+32,4),'big')))
assert rolls == [(17,1200),(20,0)],rolls
print(dict(two_interval_roll=rolls))
# Valid interior fractional positions followed by outward native motion.
coordinates=[]
for wind in [-8,0,7]:
 b=bytearray(86);struct.pack_into('>HH',b,0,0xd7ff+wind,0xd7ff+wind);struct.pack_into('>H',b,28,1024);struct.pack_into('>h',b,42,128)
 b[20]=b[21]=wind&255;b[27]=128;b[53]=b[61]=32;b[54]=244;b[57]=26;b[66]=28;b[80]=32
 c.put(p,b);assert call('endpoint_player_init',{1:owner,9:60,10:0})==0;c.put(owner,struct.pack('>II',680,680));assert call('endpoint_player_begin',{1:owner,2:p,9:20,10:1})==0;c.put(packet,bytes(10))
 for f in range(1,21):assert call('endpoint_player_step',{1:owner,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:f})==0
 xy=struct.unpack('>HH',c.get(p,4));fr=struct.unpack('>II',c.get(owner,8));coordinates.append(dict(wind=wind,xy=xy,fractions=fr))
 assert xy==(0xd800+wind,)*2 and fr==(0,0),(wind,xy,fr)
print(dict(coordinates=coordinates));c.close()
