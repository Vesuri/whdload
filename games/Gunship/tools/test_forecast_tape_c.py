"""Bounded forecast publication and exact lookup against captured frame pairs."""
from unicorn_b import *
import json
from functools import lru_cache
base=0x100000;l=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
sym=lru_cache(None)(sym)
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
tape=0x300002;owner=0x310000;player=0x311000;packet=0x312000;context=0x313000;result=0x314000;out=0x315002;size=sym('FCT_RECORDS')+20*(sym('EP_SIZE')+90)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
bad=[];lookup=[False];instruction_count=[0];hit_costs=[]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
@CODE
def instruction(handle,a,n,user):instruction_count[0]+=1
ich=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(ich),1<<2,instruction,None,1,0))
@MEM
def read(handle,kind,a,n,v,user):
 allowed=[(tape,tape+size),(owner,owner+sym('EP_SIZE')),(player,player+86),(packet,packet+4),(context,context+24),(result,result+86),(out,out+86),(0x8e000,0x8f004)]
 if not any(lo<=a and a+n<=hi for lo,hi in allowed):bad.append(('read',hex(a),n))
rh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(rh),1<<10,read,None,1,0))
@MEM
def write(handle,kind,a,n,v,user):
 allowed=(out,out+86) if lookup[0] else (tape,tape+size)
 if not(allowed[0]<=a and a+n<=allowed[1] or 0x8e000<=a and a+n<=0x8f004):bad.append((hex(a),n))
hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<11,write,None,1,0))
def call(name,args):
 regs={r:0x1300+r for r in range(1,17) if r!=8};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 start=instruction_count[0]
 lookup[0]=name=='forecast_tape_lookup';c.rw(8,0x8f000);c.call(base+sym(name))
 assert c.rr(18)==0x90000 and not bad,bad
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 assert c.get(tape-2,2)==c.get(tape+size,2)==b'ZZ'
 if lookup[0] and c.rr(9)==0:hit_costs.append(instruction_count[0]-start)
 return c.rr(9)
def load(ep,p,xy):c.put(owner,ep);c.put(player,p);c.put(packet,xy)
def find():return call('forecast_tape_lookup',{1:tape,2:owner,3:player,4:packet,5:context,6:out})
def miss():
 old=c.get(tape,size);c.put(out-2,b'Z'*90);assert find()==0xfffffffd
 assert c.get(out-2,90)==b'Z'*90 and c.get(tape,size)==old
c.put(tape-2,b'Z'*(size+4));c.put(tape,bytes(size));pairs=0;context_rejects=0
for run in ('forecast-dependencies-pal-020','forecast-dependencies-pal-060'):
 rows=json.loads((root/'tmp/c'/run/'remaining-forecast-audit.json').read_text())['reports']
 for a,b in zip(rows,rows[1:]):
  if a['world']!=b['world']:continue
  key=struct.pack('>6I',7,a['world'],0x420000,0x430000,0x440000,0);c.put(context,key)
  assert call('forecast_tape_begin',{1:tape,2:context})==0
  points=[dict(owner=a['source_owner'],player=a['source_player'])]+[v for v in a['checkpoints'] if int.from_bytes(bytes.fromhex(v['owner'])[sym('EP_DONE'):sym('EP_DONE')+2],'big')<a['span']]
  for point in points:
   load(bytes.fromhex(point['owner']),bytes.fromhex(point['player']),bytes.fromhex(a['held']))
   assert call('forecast_tape_append',{1:tape,2:owner,3:player,4:packet})==0
   miss() # publication cannot leak a partial tape
  c.put(result,bytes.fromhex(a['forecast_player']));assert call('forecast_tape_finish',{1:tape,2:result})==0
  load(bytes.fromhex(b['source_owner']),bytes.fromhex(b['source_player']),bytes.fromhex(b['held']))
  before=c.get(tape,size);assert find()==0 and c.get(out,86)==bytes.fromhex(b['forecast_player']) and c.get(tape,size)==before
  assert c.get(out-2,2)==c.get(out+86,2)==b'ZZ';pairs+=1
  for off in range(24):
   c.put(context+off,bytes([key[off]^1]));miss();context_rejects+=1;c.put(context+off,key[off:off+1])
  c.put(player+57,bytes([c.get(player+57,1)[0]^1]));miss()
  assert call('forecast_tape_reset',{1:tape})==0;miss()
  old=c.get(tape,size);assert call('forecast_tape_append',{1:tape,2:owner,3:player,4:packet})==0xfffffffd and c.get(tape,size)==old
# Capacity, wrapping stamps, nonconsecutive insertion and changed held input.
c.put(context,struct.pack('>6I',8,0,1,2,3,0));assert call('forecast_tape_begin',{1:tape,2:context})==0
p=bytes(86);ep=bytearray(sym('EP_SIZE'));xy=bytes(4);stamp=sym('EP_DELAY')+sym('CD_FIELD')
for index in range(20):
 struct.pack_into('>I',ep,stamp,(0xfffffff8+index)&0xffffffff);load(ep,p,xy)
 if index:
  saved=c.get(tape,size);c.put(packet,b'\0\1\0\0');assert call('forecast_tape_append',{1:tape,2:owner,3:player,4:packet})==0xfffffffd and c.get(tape,size)==saved;c.put(packet,xy)
  c.put(owner+stamp,struct.pack('>I',(0xfffffff9+index)&0xffffffff));assert call('forecast_tape_append',{1:tape,2:owner,3:player,4:packet})==0xfffffffd and c.get(tape,size)==saved;c.put(owner,ep)
 assert call('forecast_tape_append',{1:tape,2:owner,3:player,4:packet})==0
saved=c.get(tape,size);assert call('forecast_tape_append',{1:tape,2:owner,3:player,4:packet})==0xfffffffd and c.get(tape,size)==saved
c.put(result,p);assert call('forecast_tape_finish',{1:tape,2:result})==0
for index in range(20):
 struct.pack_into('>I',ep,stamp,(0xfffffff8+index)&0xffffffff);c.put(owner,ep);assert find()==0
for field in (0xfffffff7,12):c.put(owner+stamp,struct.pack('>I',field));miss()
# Corrupt counts are rejected before selecting any checkpoint.
for count in (0,21,65535):c.put(tape+2,struct.pack('>H',count));miss()
assert call('forecast_tape_reset',{1:tape})==0
saved=c.get(tape,size);assert call('forecast_tape_finish',{1:tape,2:result})==0xfffffffd and c.get(tape,size)==saved
c.put(context,bytes(24));assert call('forecast_tape_begin',{1:tape,2:context})==0xfffffffd and c.get(tape,size)==saved
report=dict(status='passed',captured_pair_hits=pairs,context_byte_rejections=context_rejects,capacity=20,wrap_hits=20,partial_publication_rejected=True,retirement_rejected=True,tape_bytes=size,write_bounds=True,read_bounds=True,abi_preserved=True,captured_hit_instruction_range=[min(hit_costs[:pairs]),max(hit_costs[:pairs])])
(root/'tmp/c/forecast-tape-test.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
