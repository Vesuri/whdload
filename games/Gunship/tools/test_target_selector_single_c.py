"""Prove visibility-independent selector bytes against native selection."""
from unicorn_b import *
import json,random
base=0x100000;l=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
live=(build/'selector-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
d=root/'tmp/c/homing-selection-pal-060/world-27';h=struct.unpack_from('>9I',(d/'arena.bin').read_bytes(),ls('RT_HUNKS'));c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
for i in (0,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
work=0x300000;out=0x310002;rng=random.Random(0xaa0a)
def call(name,args):
 for r,v in args.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000
 return c.rr(9)
assert call('target_select_prepare',{1:h[0],2:h[6],3:work})==0
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[]
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not(out<=a and a+n<=out+12 or 0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<11,write,None,1,0))
cases=0
for count in (0,1):
 for status in (0,1,2,255):
  for pixel in range(256):
   state=bytearray(rng.randbytes(168));state[0]=status;struct.pack_into('>H',state,2,count)
   for i,off in enumerate(rng.sample([0,18,36,54,72],5)):struct.pack_into('>H',state,8+2*i,off)
   c.put(work+sym('WT_STATE'),state);c.put(work+sym('WT_PIXELS'),bytes([pixel])*6);c.put(work+sym('WT_PALETTE')+24,bytes([24,25]))
   before=c.get(work,sym('WT_SIZE'));c.put(out-2,b'Z'*16)
   regs={r:0x1400+r for r in range(1,17) if r!=8};regs.update({1:work,2:out})
   checking=True;rc=call('target_selector_single',regs);checking=False
   assert rc==0 and not bad and c.get(work,len(before))==before
   assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
   assert c.get(out-2,2)==c.get(out+12,2)==b'ZZ'
   result=c.get(out,12)
   assert call('target_select_step',{1:work,2:work+sym('WT_PIXELS'),3:work+sym('WT_PALETTE')+24})==0
   assert c.get(work+sym('WT_STATE')+108,12)==result,(count,status,pixel)
   cases+=1
rejected=0
for off,value in [(2,v) for v in (2,5,6,65535)]+[(8,v) for v in (1,74,65534)]:
 b=bytearray(state);struct.pack_into('>H',b,2,1);struct.pack_into('>H',b,off,value);c.put(work+sym('WT_STATE'),b);c.put(out-2,b'Z'*16);before=c.get(work,sym('WT_SIZE'))
 checking=True;rc=call('target_selector_single',{1:work,2:out});checking=False
 assert rc==0xfffffffd and not bad and c.get(out-2,16)==b'Z'*16 and c.get(work,len(before))==before
 rejected+=1
report=dict(status='passed',native_selector_comparisons=cases,atomic_rejections=rejected,private_write_boundary=True,registers_preserved=True)
(root/'tmp/c/target-selector-single-test.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
