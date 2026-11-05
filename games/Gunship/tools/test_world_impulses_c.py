import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88;seed=h[4]+0x3cc
deadline=bool(os.environ.get('GS_TEST_DEADLINE_RNG'));fixture='world-impulses-deadline' if deadline else 'world-impulses'
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/f'tmp/c/{fixture}.hunk')).get_segments()[0].get_data()))
listing=(root/f'tmp/c/{fixture}.lst').read_text();entry=base+int(re.search(r'^([0-9A-F]{8}) world_motion_impulses$',listing,re.M)[1],16)
ref=0x330000;packet=0x340000;c.put(ref,c.get(h[0]+0x937c,0x116)+bytes.fromhex('4e75'))
rng_entry=h[0]+0x7a5c;record=0x360000
if deadline:
 prepare=base+int(re.search(r'^([0-9A-F]{8}) world_rng_prepare$',listing,re.M)[1],16)
 rng_entry=0x370000
 c.rw(1,h[0]+0x7a5c);c.rw(2,rng_entry);c.rw(3,record);c.rw(4,h[2]);c.rw(8,0x8f000);c.call(prepare);assert c.rr(9)==0
rng=random.Random(0x7a5c);imp=[0,0,0];draws=0;checking=False;badwrites=[]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
sb=lambda v:(v&255)-256 if v&128 else v&255
@CODE
def capture(handle,a,n,user):
 global draws
 if a in (h[0]+0x7a5c,rng_entry):draws+=1
 elif a==h[0]+0x538e:imp[0]=sb(c.rr(9))*4
 elif a==h[0]+0x53ea:imp[1]=sb(c.rr(9))
 else:imp[2]=sb(c.rr(9))
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not (packet+4<=a and a+n<=packet+10 or seed<=a and a+n<=seed+4 or 0x8d000<=a and a+n<=0x90000):badwrites.append((a,n))
hooks=[]
for addr in set([h[0]+0x7a5c,rng_entry,h[0]+0x538e,h[0]+0x53ea,ref+0x112]):
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,capture,None,addr,addr));hooks.append(hook)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)
cases=0;seen=set();drawcounts=set()
for mode,damage,height,speed,variant in itertools.product([0,1],[0,1,2,3],[0,1,255,256,512],[0,7,8,127,255,-1],range(16)):
 b=bytearray(rng.randbytes(86));struct.pack_into('>H',b,14,damage);struct.pack_into('>H',b,28,height);struct.pack_into('>h',b,42,speed)
 initialseed=rng.randbytes(4);c.put(p,b);c.put(seed,initialseed);c.put(h[6]+0x45cc,bytes([mode]));c.put(h[2]+0x14,rng.randbytes(8));c.put(h[6]+0x4294,bytes(2));c.put(h[0]+0x5524,bytes(1));imp[:]=[0,0,0];draws=0
 c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x5376)
 c.rw(6,p);c.rw(8,0x8f000);c.call(ref)
 stamp=c.get(h[2]+0x14,8)
 expected=tuple(imp);expected_seed=c.get(seed,4);expected_draws=draws
 c.put(p,b);c.put(seed,initialseed);raw=rng.randbytes(14);c.put(packet-2,raw);draws=0
 if deadline:
  c.put(record+32,stamp);live=rng.randbytes(8);c.put(h[2]+0x14,live)
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:p,2:packet,3:rng_entry})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);checking=True;c.call(entry);checking=False
 assert c.rr(9)==0 and c.rr(8)==0x8f004 and all(c.rr(r)==v for r,v in regs.items() if r!=9)
 assert struct.unpack('>hhh',c.get(packet+4,6))==expected,(mode,damage,height,speed,expected)
 assert c.get(seed,4)==expected_seed and draws==expected_draws
 assert c.get(p,86)==b and c.get(packet-2,6)==raw[:6] and c.get(packet+10,2)==raw[-2:] and not badwrites
 if deadline:assert c.get(h[2]+0x14,8)==live and c.get(record+32,8)==stamp
 seen.add(expected);drawcounts.add(draws);cases+=1
r=dict(native_cases=cases,draw_counts=sorted(drawcounts),impulse_triples=sorted(seen),unexpected_writes=badwrites,scope=('native impulses with private deadline RNG timestamps and unrelated live input; world scheduling/replay integration pending' if deadline else 'native eligibility/order/seed with frozen inputs; world scheduling/replay integration pending'),deadline_binding=deadline)
(root/f'tmp/c/{fixture}-tests.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='impulse_triples'});c.close()
