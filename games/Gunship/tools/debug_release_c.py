__file__=__file__.replace('debug_release_c.py','test_runtime_actor_release_c.py')
exec(open(__file__).read().split('for rate in (50,60):')[0])
setup(50);c.put(p+0x4d,b'\1');c.put(h[0]+0xb3b2,bytes.fromhex('70004e75'))
from capstone import *
md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
@CODE
def dbg(handle,a,n,user):
 print(hex(a-ptr('WEAPONS')),next(md.disasm(c.get(a,12),a)).mnemonic, 'p4d',c.get(p+0x4d,1).hex(),'fire',c.get(ptr('FIRE'),2).hex(),'inhibit',c.get(h[0]+0x9c42,1).hex())
hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<2,dbg,None,ptr('WEAPONS'),ptr('WEAPONS')+0x3fe))
for n in range(1,18):publish_fire(n);assert pump()==0
c.close()
