"""Exact forecast checkpoint admission against captured later frame states."""
from unicorn_b import *
import json
base=0x100000;l=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()));owner=0x300000;player=0x301000;checkpoint=0x302000;packet=0x303000
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
allowed=[(owner,owner+sym('EP_SIZE')),(player,player+86),(checkpoint,checkpoint+sym('FC_CONTROL')+4),(packet,packet+4),(0x8e000,0x8f004)];bad=[]
@MEM
def read(handle,kind,a,n,v,user):
 if not any(lo<=a and a+n<=hi for lo,hi in allowed):bad.append(('read',hex(a),n))
@MEM
def write(handle,kind,a,n,v,user):
 if not(0x8e000<=a and a+n<=0x8f004):bad.append(('write',hex(a),n))
hooks=[]
for kind,fn in ((1<<10,read),(1<<11,write)):
 hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),kind,fn,None,1,0));hooks.append(hk)
def match():
 regs={r:0x1200+r for r in range(1,17) if r!=8};regs.update({1:owner,2:player,3:checkpoint,4:packet})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym('forecast_checkpoint_match'))
 assert c.rr(18)==0x90000 and not bad,bad
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 return c.rr(9)
cases=0;negative=0
for run in ('forecast-dependencies-pal-020','forecast-dependencies-pal-060'):
 reports=json.loads((root/'tmp/c'/run/'remaining-forecast-audit.json').read_text())['reports']
 for a,b in zip(reports,reports[1:]):
  if a['world']!=b['world']:continue
  step=next(x for x in a['checkpoints'] if x['field']==b['source_field'])
  cp=bytes.fromhex(step['owner']+step['player']+a['held']);c.put(checkpoint,cp)
  c.put(owner,bytes.fromhex(b['source_owner']));c.put(player,bytes.fromhex(b['source_player']));c.put(packet,bytes.fromhex(b['held']))
  assert match()==0;cases+=1
  # Every byte matters: include timestamps, history, fractions, non-motion
  # command fields and both held directions. No mask silently ignores changes.
  for address,length in ((owner,sym('EP_SIZE')),(player,86),(packet,4)):
   original=c.get(address,length)
   for off in range(length):
    c.put(address+off,bytes([original[off]^1]));assert match()==0xfffffffd;negative+=1
    c.put(address+off,original[off:off+1])
  assert c.get(checkpoint,len(cp))==cp
report=dict(status='passed',captured_matches=cases,single_byte_rejections=negative,no_overreads=True,stack_only_writes=True,registers_preserved=True)
(root/'tmp/c/forecast-checkpoint-test.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
