"""Collector relocation validation and scene setup failure checks."""
from unicorn_b import *
from layout import locate
import json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();c.put(0x200000,mem);c.put(base,blob);scene=0x110000;target=0x120000;collector=0x130000;size=sym('WTC_CODE_SIZE')
def run(name):
 rs={1:h[0],2:h[4],3:h[6],4:scene,5:target,6:collector,8:0x8f000}
 for r,v in rs.items():c.rw(r,v)
 c.call(addr(name));assert all(c.rr(r)==(0x8f004 if r==8 else v) for r,v in rs.items())
 return c.rr(9)
assert run('target_collect_prepare')==0
relocs=[struct.unpack('>4H',c.get(addr('target_collect_relocs')+8*i,8)) for i in range(31)]
expected=bytearray(c.get(h[0]+0xa450,size))
for off,arg,original,dest in relocs:
 if dest!=65535:struct.pack_into('>I',expected,off,(target+(dest&32767)) if dest&32768 else scene+dest)
assert c.get(collector,size)==expected
rejects=0
for off in [0,size-2]+[off+d for off,_,_,_ in relocs for d in (0,2)]:
 a=h[0]+0xa450+off;old=c.get(a,2);c.put(a,bytes(v^1 for v in old));c.put(collector-2,b'Z'*(size+4))
 assert run('target_collect_prepare')==0xffffffff and c.get(collector-2,size+4)==b'Z'*(size+4)
 c.put(a,old);rejects+=1
site_rejects=0
for off in [s+d for s in (0x63b0,0x63c4,0x63ce,0x63d4) for d in (0,2,4)]:
 a=h[0]+off;old=c.get(a,2);c.put(a,bytes(v^1 for v in old));before=c.get(scene,(sym('SCT_COLLECTOR')+4))
 assert run('scene_target_prepare')==0xffffffff and c.get(scene,(sym('SCT_COLLECTOR')+4))==before
 c.put(a,old);site_rejects+=1
assert run('scene_target_prepare')==0
assert c.get(scene+sym('SCT_TARGET'),8)==struct.pack('>II',target,collector)
print(json.dumps(dict(status='passed',collector_rejections=rejects,draw_site_rejections=site_rejects,relocations=31)));c.close()
