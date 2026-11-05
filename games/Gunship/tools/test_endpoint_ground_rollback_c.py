exec(open(__file__.replace('test_endpoint_ground_rollback_c.py','test_endpoint_ground_preview_c.py')).read().split('resets=notifications=0')[0])
# Fresh CPU has not executed completion yet, so the hook instruments it.
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
observed=[]
@CODE
def corrupt(handle,a,n,user):
 observed.append(c.get(event,4))
 # Corrupt only the prepared candidate's flight rate, after ground evaluation.
 c.put(c.rr(6)+12,struct.pack('>H',99))
hook=C.c_size_t();entry=base+sym('player_boundary_complete');ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,corrupt,None,entry,entry))
b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);b[27]=128;b[57]=30;b[66]=28
c.put(p,b);c.put(event,bytes(4));c.put(packet,bytes(10));c.put(counter,bytes(4));c.put(h[6]+0x42f6,bytes(1));c.put(binding,struct.pack('>II',ground,event))
assert call('player_step_init',{1:shadow,9:3,10:0})==0
before=c.get(p,86),c.get(shadow,76)
assert call('endpoint_ground_preview',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,7:binding,9:1})==0xffffffff
assert observed and observed[0][-1]==1
assert before==(c.get(p,86),c.get(shadow,76)) and c.get(event,4)==bytes(4)
assert c.get(counter,4)==bytes(4) and c.get(h[6]+0x42f6,1)==bytes(1)
print(dict(failure_after_ground_ready=True,state_and_player_unchanged=True,event_discarded=True,no_native_effects=True))
c.close()
