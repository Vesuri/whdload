exec(open(__file__.replace('test_scheduled_endpoint_faults_c.py','test_scheduled_endpoint_c.py')).read().split('runs=[]')[0])
def ready():
 for name,args in [('clock_init',{1:TC,9:0,10:50}),('history_init',{1:TH,9:0}),('commands_init',{1:CQ,9:0}),('scheduler_init',{1:TS,2:TC,3:TH,4:CQ}),('endpoint_player_init',{1:shadow,9:50,10:0})]:assert call(name,args)==0
 c.put(context,struct.pack('>6I',shadow,p,stages,h[0]+0x7a44,packet,TS)+bytes(6))
 b=bytearray(86);struct.pack_into('>H',b,28,1024);b[27]=128;b[57]=26;b[66]=28;c.put(p,b)
 c.put(sample,struct.pack('>10I',1,1,0,0,0,0,0,0,0,0));assert call('history_publish',{1:TH,2:sample})==1
 assert call('scheduler_begin',{1:TS,9:128,10:8})==0
 assert call('scheduler_next',{1:TS,2:rec})==1
 c.put(packet,struct.pack('>hhhhh',1,0,0,0,0))
args={1:context,2:rec,9:1};failures=0
for kind in ['field','cutoff','rate','control','tick','phase','due','fraction','fault']:
 ready();expected=0xfffffffd
 if kind=='field':c.put(rec,struct.pack('>I',2))
 if kind=='cutoff':c.put(rec+20,struct.pack('>I',1))
 if kind=='rate':c.put(TC+22,struct.pack('>H',60))
 if kind=='control':c.put(packet,struct.pack('>h',2));expected=0xffffffff
 if kind=='phase':c.put(TC+20,struct.pack('>H',7))
 if kind=='due':c.put(TS+14,struct.pack('>H',1))
 if kind=='fraction':c.put(shadow+36,struct.pack('>I',1360));expected=0xffffffff
 if kind=='fault':c.put(TH+6,struct.pack('>H',1));expected=0xffffffff
 before=c.get(p,86),c.get(shadow,164)
 assert call('scheduled_endpoint_step',args|({9:65536} if kind=='tick' else {}))==expected,kind
 assert before==(c.get(p,86),c.get(shadow,164)) and word(context+28)==0 and c.get(TS+32,4)==bytes(4)
 failures+=1
for world_only in [False,True]:
 ready();assert call('commands_publish',{1:CQ,9:1,10:0x51})==1
 c.put(TS+28,struct.pack('>I',1));c.put(rec+20,struct.pack('>I',1))
 if world_only:
  # Set an internally consistent final interval field to isolate world cursor.
  c.put(CQ+2,struct.pack('>H',1));c.put(TS+14,struct.pack('>H',1))
  c.put(shadow+158,struct.pack('>HHH',17,16,1));c.put(TC+20,struct.pack('>H',1))
 before=c.get(p,86),c.get(shadow,164),c.get(CQ,1048)
 assert call('scheduled_endpoint_step',args)==0xfffffffd
 assert before==(c.get(p,86),c.get(shadow,164),c.get(CQ,1048));failures+=1
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
for after in [False,True]:
 c.close();c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-endpoint.hunk')).get_segments()[0].get_data()))
 assert call('motion_stages_prepare',{1:h[0],2:stages})==0
 ready();before=c.get(p,86),c.get(shadow,164)
 @CODE
 def fault(handle,a,n,user):c.put(TH+6,struct.pack('>H',1))
 hook=C.c_size_t();entry=base+sym('scheduler_player_done' if after else 'endpoint_player_step_private')
 ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fault,None,entry,entry))
 assert call('scheduled_endpoint_step',args)==0xffffffff
 assert word(context+28)==int(after) and int.from_bytes(c.get(TS+32,4),'big')==int(after)
 assert (before==(c.get(p,86),c.get(shadow,164)))== (not after)
 # Clearing faults cannot replay a step already acknowledged after publication.
 if after:
  c.put(TH+6,bytes(2));c.put(TS+22,bytes(2));assert call('scheduled_endpoint_step',args)==0xfffffffd
print(dict(rejections=failures,before_publication_rollback=True,after_publication_counted_once=True,calls=calls))
c.close()
