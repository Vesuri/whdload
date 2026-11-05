import textwrap
source=open(__file__.replace('test_flight_consumer_faults_c.py','test_flight_consumer_c.py')).read()
exec(source.split('runs=[]')[0])
setup=textwrap.dedent(source[source.index('  c.put(low,initial)'):source.index('  tick=65532')])
def init():
 global rate
 rate=50;exec(setup,globals())
def word(a):return int.from_bytes(c.get(a,2),'big')
def long(a):return int.from_bytes(c.get(a,4),'big')
def snapshot():return [c.get(a,n) for a,n in [(low,length),(TF,68),(TS,48),(CQ,1048),(shadow,164),(EVENT,4),(SI,38)]]
def deliver(f,command=None):
 if command is not None:assert call('commands_publish',{1:CQ,9:f,10:command})==1
 cutoff=long(CQ+12)
 c.put(sample,struct.pack('>6IHhhHII',f,0,0,0,0,cutoff,8,0,0,0,1,f))
 assert call('history_publish',{1:TH,2:sample})==1
 assert call('scheduler_begin',{1:TS,9:128,10:8})==0
 assert call('scheduler_next',{1:TS,2:rec})==1

def consume(budget=128):return call('timing_flight_consume',{1:TF,9:budget})
init();deliver(1)
for budget in (0,129,0xffffffff):
 before=snapshot();assert consume(budget)==0xfffffffd;assert snapshot()==before
old=c.get(rec,4);c.put(rec,bytes(4));before=snapshot();assert consume()==0xfffffffd;assert snapshot()==before;c.put(rec,old)
# Retained lifecycle command does not admit motion or replay field timers.
init();deliver(1,0x45);assert consume()==2
assert word(TF+60)==1 and long(TS+32)==0 and word(CQ+2)==0
before=snapshot();assert consume()==2;assert snapshot()==before
# Ordinary command-budget return resumes without running field/opening again.
init();deliver(1,0x51);assert consume(1)==0xfffffffe
assert word(TF+60)==1 and long(TS+32)==0
assert consume(1)==0 and long(TS+32)==1
# Native script modal keeps the world pending, and cannot be restarted here.
init();c.put(p+83,b'\2\1')
for f in range(1,18):
 deliver(f);status=consume();assert status==(3 if f==17 else 0),(f,status)
assert word(TF+60)==5 and word(TS+12)==2 and long(TS+36)==0 and word(BODY+28)==1
before=snapshot();assert consume()==0xfffffffd;assert snapshot()==before
# A positive geometry result ends the flight and acknowledges cleanup once.
init();c.put(p,struct.pack('>HH',0x7fff,0x7fff));c.put(p+28,bytes(2));c.put(p+27,bytes(1));c.put(p+57,bytes(1));c.put(p+66,bytes(1));c.put(p+26,bytes(1))
assert call('control_mode_init',{1:MODE,2:p})==0
for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],struct.pack('>HHH',0x7fff,0x7fff,24)):c.put(h[6]+off,bytes([v]))
for f in range(1,18):
 deliver(f);status=consume();assert status==(4 if f==17 else 0),('end',f,status)
assert word(TF+60)==6 and word(TS+12)==0 and long(TS+36)==1 and word(BODY+28)==3
before=snapshot();assert consume()==0xfffffffd;assert snapshot()==before
# Producer fault exactly after publication: step counts once, replay is latched out.
init()
for f in range(1,17):
 deliver(f);assert consume()==0
deliver(17)
@CODE
def fault(handle,a,n,user):c.put(CQ+8,b'\0\1')
hh=C.c_size_t();addr=base+sym('scheduler_player_done');ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,fault,None,addr,addr))
assert consume()==0xffffffff
assert word(TF+60)==7 and long(TS+32)==17 and word(context+28)==1
assert c.get(EVENT,4)==bytes(4) and long(TS+36)==0 and word(TS+12)==2
before=snapshot();assert consume()==0xffffffff;assert snapshot()==before
print(json.dumps(dict(status='passed',calls=calls,modal_retained=True,post_publication_counted_once=True,command_budget_resumed=True)));c.close()
