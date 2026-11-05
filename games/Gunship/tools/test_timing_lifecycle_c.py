"""Execute coordinated pause/rebase with real clock, queues and endpoint state."""
from unicorn_b import *
import random,json
from layout import locate
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/lifecycle.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/lifecycle.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
T=0x300000;H=0x310000;Q=0x320000;S=0x330000;EP=0x340000;R=0x350000;O=0x360000
P=0x370000;STAGES=0x380000;PACKET=0x390000
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c.put(0x200000,mem)
rng=random.Random(382);calls=0
BAD=0xfffffffd
regions=[(T,28),(H,5140),(Q,1048),(S,48),(EP,164),(P,86)]
def snap():return [c.get(a,n) for a,n in regions]
def w(a):return int.from_bytes(c.get(a,2),'big')
def l(a):return int.from_bytes(c.get(a,4),'big')
def pw(a,v):c.put(a,struct.pack('>H',v))
def pl(a,v):c.put(a,struct.pack('>I',v&0xffffffff))
def call(n,args={},expect=0):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(args)
 for r,v in regs.items():c.rw(r,v&0xffffffff)
 c.rw(8,0x8f000);c.call(base+sym(n));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,n
 assert c.rr(9)==expect,(n,c.rr(9),expect)
 assert all(c.rr(r)==v&0xffffffff for r,v in regs.items() if r!=9),(n,'registers')
def init(rate):
 call('clock_init',{1:T,9:0,10:rate});call('history_init',{1:H,9:0});call('commands_init',{1:Q,9:0})
 call('scheduler_init',{1:S,2:T,3:H,4:Q});call('endpoint_player_init',{1:EP,9:rate,10:0})
def publish(f):
 c.put(R,bytes(40));pl(R,f);call('history_publish',{1:H,2:R},1)
def resume(epoch=1000,seq=500,prev=-1,expect=0):call('timing_resume',{1:S,2:EP,9:epoch,10:seq,11:prev},expect)
def reject(**args):
 before=snap();resume(expect=BAD,**args);assert before==snap()
call('motion_stages_prepare',{1:h[0],2:STAGES})
runs=[]
for rate in (50,60):
 for epoch in (1000,0xffffffff):
  init(rate)
  player=bytearray(86);struct.pack_into('>HH',player,0,0x8000,0x8000);struct.pack_into('>H',player,28,1024);player[27]=128;player[57]=26;player[66]=28;c.put(P,player)
  # Seven completed fields, then ten queued records discarded on suspension.
  for f in range(1,18):publish(f)
  call('scheduler_begin',{1:S,9:7,10:3})
  for _ in range(7):call('scheduler_next',{1:S,2:O},1);call('scheduler_player_done',{1:S})
  for seq in range(1,4):call('commands_publish',{1:Q,9:seq,10:0x1234},1)
  pw(Q+2,2);pw(Q+4,1) # two retained slots, not the sum of unread readers
  c.put(EP,struct.pack('>10I',*([680]*10)));pw(EP+158,17);pw(EP+160,7)
  reject() # active owners cannot be rebased
  call('timing_suspend',{1:S});assert w(T+24)==w(H+4)==w(Q+6)==0
  assert l(H+12)==10 and w(H)==w(H+2)==17 and w(S+16)==0
  retained=c.get(Q,1048);publish_inactive=c.get(H,5140)
  call('history_publish',{1:H,2:R});call('commands_publish',{1:Q,9:4,10:1})
  assert c.get(Q,1048)==retained and c.get(H,5140)==publish_inactive
  call('timing_suspend',{1:S});assert l(H+12)==10
  for prev in (-2,2,65535):reject(prev=prev)
  pw(T+22,3);reject();pw(T+22,rate)
  for addr in (T+24,H+4,Q+6):pw(addr,1);reject();pw(addr,0)
  for phase in (1,2):pw(S+12,phase);reject();pw(S+12,0)
  # Fault recovery retains diagnostics, clears stale endpoint input/motion.
  for addr in (T+26,H+6,Q+8,S+22):pw(addr,1)
  pl(H+8,9);pl(Q+16,4)
  resume(epoch=epoch)
  assert c.get(P,86)==player
  assert l(T)==l(H+16)==l(S+24)==epoch and l(Q+12)==l(S+28)==500
  assert l(T+4)==7 and l(T+12)==21 and l(T+16)==1 and w(T+20)==0
  assert l(S+32)==7 and l(S+36)==0 and l(H+12)==10 and l(Q+20)==2
  assert l(H+8)==9 and l(Q+16)==4
  assert c.get(EP,40)==bytes(40) and c.get(EP+72,92)==bytes(92)
  assert w(EP+40)==rate and c.get(EP+52,20)==b'\xff'*20
  assert all(w(a)==0 for a in (T+26,H+6,Q+8,S+22))
  # First fresh deadline is a full interval away, including field-stamp wrap.
  span=(rate+2)//3
  call('endpoint_player_begin',{1:EP,2:P,9:span,10:1});c.put(PACKET,bytes(10))
  for n in range(1,span+1):publish((epoch+n)&0xffffffff)
  call('scheduler_begin',{1:S,9:128,10:3})
  for n in range(1,span+1):
   call('scheduler_next',{1:S,2:O},1)
   call('endpoint_player_step',{1:EP,2:P,3:STAGES,4:h[0]+0x7a44,5:PACKET,9:(epoch+n)&0xffffffff})
   assert l(EP+48)==(epoch+n)&0xffffffff
   call('scheduler_player_done',{1:S},int(n==span))
  # Modal pause retains due world ownership. Resume cannot silently abandon it.
  call('timing_suspend',{1:S});reject(epoch=2000)
  assert w(S+12)==2 and l(S+36)==0
  call('scheduler_world_done',{1:S},0xffffffff) # completion counted despite inactive upstream
  assert l(S+36)==1 and w(S+12)==0
  call('scheduler_world_done',{1:S},BAD)
  completed=c.get(P,86)
  resume(epoch=2000,seq=501,prev=1)
  assert c.get(P,86)==completed
  assert l(S+32)==7+span and l(S+36)==1 and w(S+12)==0
  assert c.get(EP+52,20)==b'\1'*20
  call('scheduler_world_done',{1:S},BAD)
  runs.append(dict(rate=rate,epoch=epoch,first_deadline=span,worlds=l(S+36)))
print(json.dumps(dict(status='passed',calls=calls,runs=runs)));c.close()
