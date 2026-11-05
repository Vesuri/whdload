exec(open(__file__.replace('test_endpoint_yaw_c.py','test_endpoint_owner_c.py')).read().split('report=json.loads')[0])
cases=0;steps=0;cleared=0;retained=0
for rate,span in [(3,1),(50,17),(50,16),(60,20)]:
 for height in [0,1024]:
  for pitch in [-128,-12,-4,-3,-1,0,1,20,127]:
   b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,height);b[54]=pitch&255;b[63]=3;b[27]=128;b[57]=30;b[66]=28
   c.put(LIVE,b);call('endpoint_player_init',{1:OWNER,9:rate,10:0});call('endpoint_player_begin',{1:OWNER,2:LIVE,9:span,10:1})
   c.put(PACKET,bytes(10))
   for field in range(1,span+1):
    # A new yaw command before the deadline must feed the same native branch.
    yaw=3 if field<(span+1)//2 else 254;c.put(LIVE+63,bytes([yaw]))
    effective=bytearray(b);effective[63]=yaw;c.put(P,effective)
    call('player_step_init',{1:SH,9:3,10:0});call('player_step_interval',{1:SH,2:P,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:1})
    expected=c.get(P+63,1)[0]
    call('endpoint_player_step',{1:OWNER,2:LIVE,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:field});steps+=1
    assert c.get(LIVE+63,1)[0]==(expected if field==span else yaw),(rate,height,pitch,field,expected)
   cleared+=expected==0;retained+=expected!=0;cases+=1
assert cleared and retained
print(dict(cases=cases,fields=steps,native_clears=cleared,native_retains=retained,mid_interval_commands=True))
c.close()
