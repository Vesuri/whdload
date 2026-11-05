from unicorn_b import *
from layout import locate
mem=(root/'tmp/d4-smoke/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def a(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def putl(c,p,n):c.put(p,struct.pack('>I',n))
def putw(c,p,n):c.put(p,struct.pack('>H',n))
def getl(c,p):return int.from_bytes(c.get(p,4),'big')
def setup():
 c=CPU();c.put(0x200000,mem);c.put(base,blob);arena=0x600000
 putl(c,a('timing_runtime_arena'),arena);c.put(arena+a('RT_HUNKS')-base,struct.pack('>9I',*h));putw(c,arena+a('RT_CAPTURE_OWNER')-base,1)
 return c,arena
sites=(0x4868,0xace2,0xaf56,0xb0d0,0xb574,0xb5d6)
for allocation in (0,0x120000):
 c,arena=setup()
 for s in sites:putw(c,h[0]+s,2)
 putl(c,4,0x500000);c.put(0x500000-198,bytes.fromhex('23c00052000023c100520004203c')+struct.pack('>I',allocation)+bytes.fromhex('4e75'))
 c.rw(1,arena);c.call(a('triple_install'))
 assert c.rr(9)==0
 assert (getl(c,0x520000),getl(c,0x520004))==(40000,3)
 assert getl(c,a('triple_allocation'))==allocation
 for s in sites:assert c.get(h[0]+s,2)==struct.pack('>H',3 if allocation else 2)
 c.close()
c,arena=setup();bm=0x520000;planes=[0x100000,0x110000,0x120000]
putl(c,a('timing_display_bitmap_array'),bm);putl(c,a('triple_allocation'),planes[2]);putl(c,h[0]+0x867e,0x530000);putl(c,0x530000,0x510000);c.put(0x510000-228,bytes.fromhex('4e75'))
for j,p in enumerate(planes):
 c.put(p,bytes([j+1])*40000)
 if j<2:c.put(bm+j*40,struct.pack('>HHBBH8I',40,200,0,5,0,*[p+k*8000 for k in range(5)],0,0,0))
def cache_addrs(slot):return [h[0]+0xaf98+slot+2*k for k in range(6)]+[h[6]+0x9c4+slot+12*k for k in range(7)]
def readcache(slot):return bytes(c.get(x,1)[0] for x in cache_addrs(slot))
def writecache(slot,data):
 for x,v in zip(cache_addrs(slot),data):c.put(x,bytes([v]))
writecache(0,bytes(range(13)));writecache(1,bytes(range(20,33)))
c.rw(10,0);c.call(a('triple_bind'));assert c.rr(9)==1
assert c.get(planes[2],40000)==c.get(planes[0],40000)
expected={planes[0]:readcache(0),planes[1]:readcache(1),planes[2]:readcache(0)}
front=planes[1];queued=planes[0]
for n in range(1,19):
 slot=n%2;putw(c,a('triple_rotate'),1);putw(c,a('timing_display_pending'),1)
 c.rw(10,slot);c.call(a('triple_bind'));assert c.rr(9)==1
 target=getl(c,bm+slot*40+8)
 assert target not in (front,queued),(n,hex(target),hex(front),hex(queued))
 assert readcache(slot)==expected[target],(n,readcache(slot),expected[target])
 new=bytes((n*7+k)%256 for k in range(13));writecache(slot,new);expected[target]=new
 # Another bitmap lookup during the same frame must not rotate again.
 c.rw(10,slot);c.call(a('triple_bind'));assert getl(c,bm+slot*40+8)==target
 front,queued=queued,target
assert len(set(planes))==3
c.close()
print('PASS triple allocation/fallback, initial bitmap copy, 18 rotations avoiding front/pending, 13 cache bytes follow each physical buffer')
