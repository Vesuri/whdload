exec(open(__file__.replace('test_scheduled_endpoint_ground_faults_c.py','test_scheduled_endpoint_c.py')).read().split('runs=[]')[0])
GR=0x430000;EVENT=0x431000;COUNT=0x432000
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
for after in [False,True]:
 c.close();c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-endpoint.hunk')).get_segments()[0].get_data()))
 assert call('motion_stages_prepare',{1:h[0],2:stages})==0
 c.put(h[0]+0xa150,bytes.fromhex('52b9')+struct.pack('>I',COUNT)+bytes.fromhex('4e75'))
 assert call('ground_deferred_prepare',{1:h[0],2:GR,3:h[6],4:EVENT})==0
 for name,args in [('clock_init',{1:TC,9:0,10:50}),('history_init',{1:TH,9:0}),('commands_init',{1:CQ,9:0}),('scheduler_init',{1:TS,2:TC,3:TH,4:CQ}),('endpoint_player_init',{1:shadow,9:50,10:0})]:assert call(name,args)==0
 c.put(context,struct.pack('>6I',shadow,p,stages,h[0]+0x7a44,packet,TS)+bytes(6)+struct.pack('>II',GR,EVENT))
 b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,32767);b[16]=1;b[27]=128;b[57]=30;b[62]=100;b[66]=28
 c.put(p,b);c.put(packet,bytes(10));c.put(EVENT,bytes(4));c.put(COUNT,bytes(4));c.put(h[6]+0x42f6,bytes(1))
 enabled=[False];hits=[]
 @CODE
 def fault(handle,a,n,user):
  if enabled[0]:
   hits.append(c.get(EVENT,4));c.put(TH+6,struct.pack('>H',1))
 entry=base+sym('scheduler_player_done' if after else 'endpoint_ground_resolve');hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fault,None,entry,entry))
 for f in range(1,18):
  c.put(sample,struct.pack('>10I',f,0,0,0,0,0,0,0,0,0));assert call('history_publish',{1:TH,2:sample})==1
  assert call('scheduler_begin',{1:TS,9:128,10:8})==0
  assert call('scheduler_next',{1:TS,2:rec})==1
  if f<17:assert call('scheduled_endpoint_ground_step',{1:context,2:rec,9:1})==0
 enabled[0]=True;before=c.get(p,86),c.get(shadow,164)
 assert call('scheduled_endpoint_ground_step',{1:context,2:rec,9:1})==0xffffffff
 assert hits and word(context+28)==int(after)
 assert int.from_bytes(c.get(TS+32,4),'big')==16+int(after)
 assert (before==(c.get(p,86),c.get(shadow,164)))==(not after)
 assert c.get(COUNT,4)==bytes(4) and c.get(h[6]+0x42f6,1)==bytes(1)
 if after:
  assert c.get(EVENT,4)==bytes.fromhex('0007b401'),c.get(EVENT,4).hex()
  assert call('ground_deferred_commit',{1:EVENT,2:h[0]+0xa150,3:h[6]+0x42f6})==1
  assert c.get(COUNT,4)==struct.pack('>I',1) and c.get(h[6]+0x42f6,1)==b'\xb4'
  assert call('ground_deferred_commit',{1:EVENT,2:h[0]+0xa150,3:h[6]+0x42f6})==0xffffffff
  c.put(TH+6,bytes(2));c.put(TS+22,bytes(2));assert call('scheduled_endpoint_ground_step',{1:context,2:rec,9:1})==0xfffffffd
 else:
  assert c.get(EVENT,4)==bytes(4)
  # Retrying rejected private work is permitted after explicit fault recovery.
  enabled[0]=False;c.put(TH+6,bytes(2));c.put(TS+22,bytes(2))
  assert call('scheduled_endpoint_ground_step',{1:context,2:rec,9:1})==1
  assert c.get(EVENT,4)==bytes.fromhex('0007b401')
print(dict(before_publication_event_discarded=True,after_publication_event_retained=True,notification_once=True,calls=calls))
c.close()
