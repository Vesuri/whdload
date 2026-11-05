# Reuse only the fixture loader/helpers, not the long trajectory run.
exec(open(__file__.replace('test_endpoint_owner_transactions_c.py','test_endpoint_owner_c.py')).read().split('report=json.loads')[0])
import random
rng=random.Random(164);checks=0
guards={OWNER-4:b'\xa5'*4,OWNER+OWNER_SIZE:b'\x5a'*4,LIVE-4:b'\xc3'*4,LIVE+86:b'\x3c'*4}
for a,b in guards.items():c.put(a,b)

def invoke(name,args,expected=0):
 global checks
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(args)
 for r,v in regs.items():c.rw(r,v&0xffffffff)
 c.rw(8,0x8f000);c.call(sym(name));checks+=1
 assert all(c.get(a,len(b))==b for a,b in guards.items()),name
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert c.rr(9)==expected&0xffffffff,(name,c.rr(9),expected)
 assert all(c.rr(r)==v&0xffffffff for r,v in regs.items() if r!=9),(name,'register')
def rejected(name,args):
 before=c.get(OWNER,OWNER_SIZE),c.get(LIVE,86)
 invoke(name,args,-1)
 assert before==(c.get(OWNER,OWNER_SIZE),c.get(LIVE,86))
b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);b[27]=128;b[57]=30;b[66]=28
c.put(LIVE,b);c.put(OWNER,b'\xa5'*OWNER_SIZE)
for rate,prev in [(0,0),(50,2),(65596,0)]:rejected('endpoint_player_init',{1:OWNER,9:rate,10:prev})
invoke('endpoint_player_init',{1:OWNER,9:60,10:0})
for span,tick in [(17,1),(20,65536)]:rejected('endpoint_player_begin',{1:OWNER,2:LIVE,9:span,10:tick})
args={1:OWNER,2:LIVE,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:1}
c.put(PACKET,bytes(10));rejected('endpoint_player_step',args)
invoke('endpoint_player_begin',{1:OWNER,2:LIVE,9:20,10:1});anchor=bytes(b)
history=[];pulse=[]
for field in range(1,21):
 # Field-stamped command inputs are read freshly, while motion stays anchored.
 b=bytearray(c.get(LIVE,86))
 if field==3:b[63]=2
 if field==7:b[57]=36
 if field==12:b[66]=12
 b[26]=field # view command must survive every publication
 c.put(LIVE,b);x=1 if 5<=field<=9 else 0;y=-1 if 8<=field<=13 else 0
 c.put(PACKET,struct.pack('>hhhhh',x,y,0,0,0))
 # Independent orchestration of the already-verified native preview + distributor.
 effective=bytearray(b)
 for off,width,_,_ in fields:effective[off:off+width]=anchor[off:off+width]
 effective[80]=anchor[80]
 c.put(P,effective);call('player_step_init',{1:SH,9:3,10:0})
 call('player_step_interval',{1:SH,2:P,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:1});target=c.get(P,86)
 c.put(RESIDUES,c.get(OWNER,40));distributed=distribute(anchor,target,b,20)
 expected=bytearray(b)
 for off,width,_,_ in fields:expected[off:off+width]=distributed[off:off+width]
 for off,width in [(48,2),(56,1),(58,1),(64,1),(80,1)]:expected[off:off+width]=target[off:off+width]
 if field==20:expected[63]=target[63]
 args[9]=field;invoke('endpoint_player_step',args)
 assert c.get(LIVE,86)==expected and c.get(OWNER,40)==c.get(RESIDUES,40),(field,c.get(LIVE,86).hex(),expected.hex())
 assert c.get(LIVE+63,1)==(target[63:64] if field==20 else b[63:64])
 roll=int.from_bytes(c.get(LIVE+55,1),'big',signed=True)+int.from_bytes(c.get(OWNER+32,4),'big')/1360
 pulse.append(roll)
 if field==1:
  rejected('endpoint_player_step',args)
  rejected('endpoint_player_step',dict(args,**{})|{9:3})
  rejected('endpoint_player_begin',{1:OWNER,2:LIVE,9:20,10:2})
  c.put(PACKET,struct.pack('>hhhhh',2,0,0,0,0));rejected('endpoint_player_step',args|{9:2});c.put(PACKET,bytes(10))
  for index in [2,3,4]:
   packet=[0]*5;packet[index]=1;c.put(PACKET,struct.pack('>hhhhh',*packet));rejected('endpoint_player_step',args|{9:2})
  c.put(PACKET,bytes(10))
  saved=c.get(OWNER+36,4);c.put(OWNER+36,struct.pack('>I',1360));rejected('endpoint_player_step',args|{9:2});c.put(OWNER+36,saved)
assert pulse[4]!=pulse[3] and pulse[9]!=0
rejected('endpoint_player_step',args|{9:21})
# World recoil before the next interval becomes part of the new anchor.
b=bytearray(c.get(LIVE,86));b[54]=(b[54]-4)%256;c.put(LIVE,b)
invoke('endpoint_player_begin',{1:OWNER,2:LIVE,9:20,10:2});assert c.get(OWNER+72,86)==b
c.put(PACKET,bytes(10));invoke('endpoint_player_step',args|{9:21})
# One-field mode and PAL allowed spans, with fresh lifecycle initialization.
for rate,span in [(3,1),(50,17),(50,16)]:
 invoke('endpoint_player_init',{1:OWNER,9:rate,10:0})
 invoke('endpoint_player_begin',{1:OWNER,2:LIVE,9:span,10:65535})
 invoke('endpoint_player_step',args|{9:0xffffffff})
print(dict(checks=checks,command_fields=20,pulse_responsive=True,recoil_reanchored=True,history_rollback=True,registers_preserved=True,exact_copy_bounds=True))
c.close()
