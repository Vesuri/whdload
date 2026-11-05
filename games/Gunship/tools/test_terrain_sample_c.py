"""Read-only terrain sample against native B3B2 and a separate plane oracle."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import json,random
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);c.put(0x200000,mem);bitmap=0x110000;palette=0x111000;planes=[0x120000+i*0x10000 for i in range(8)];rng=random.Random(0xb3b2)
plane_data=[rng.randbytes(65536) for i in planes]
for a,data in zip(planes,plane_data):c.put(a,data)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[]
@MEM
def writes(handle,kind,a,n,v,user):
 if checking and not(0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,writes,None,1,0))
def call(x,y,want):
 global checking
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:bitmap,2:palette,9:x,10:y});c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);bad.clear();checking=True;c.call(base+sym('terrain_sample'));checking=False
 assert c.rr(18)==0x90000 and c.rr(9)==want,(hex(x),hex(y),hex(c.rr(9)),hex(want))
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9) and not bad

def transform(x,y):
 q=(x&0xffff0000)|((x+128)&65535);q=(q&0xffff0000)|((q+2*(q&65535))&65535);q>>=9
 xx=((q-20+32768)&65535)-32768
 yy=-((((y+128)&65535)>>8)-216)*2
 return xx,yy
matched=blocked=unknown=0;upper_effect=0
for case in range(6000):
 row=rng.choice([16,40,80]);rows=rng.choice([100,200,512]);depth=1+case%8;mode=case%2
 c.put(bitmap,struct.pack('>HHBBH8I',row,rows,0,depth,0,*planes));c.put(h[6]+0x47c4,struct.pack('>I',bitmap));c.put(h[6]+0x3b9e,bytes([mode]))
 x=(rng.choice([0,0,0,0x10000,0xffff0000,0x12340000])|rng.randrange(65536));y=rng.randrange(0x100000000);xx,yy=transform(x,y)
 colors=bytes([rng.randrange(256),rng.randrange(256)]);c.put(palette,colors);c.put(h[6]+0x16dc+mode*256+24,colors)
 if not(0<=xx<row*8 and 0<=yy<rows):call(x,y,0xfffffffd);unknown+=1;continue
 offset=yy*row+xx//8;pixel=sum(((plane_data[i][offset]>>(7-xx%8))&1)<<i for i in range(depth))
 if case%3==0:colors=bytes([pixel,rng.randrange(256)]);c.put(palette,colors);c.put(h[6]+0x16dc+mode*256+24,colors)
 want=0xffffffff if pixel in colors else 0
 c.rw(9,x);c.rw(10,y);c.rw(8,0x8f000);c.call(h[0]+0xb3b2)
 assert c.rr(18)==0x90000 and c.rr(9)==want,(case,xx,yy,pixel,c.rr(9),want)
 before=c.get(0x97ee00,0x21200);call(x,y,want);assert c.get(0x97ee00,0x21200)==before
 matched+=1;blocked+=want==0xffffffff;upper_effect+=transform(x&65535,y)!=transform(x,y)
# Valid transformed coordinate (10,100), then malformed bitmap descriptors.
x=5000;y=(216-50)*256-128
assert transform(x,y)==(10,100)
invalid=0
for row,rows,depth,ps in [(0,200,5,planes),(40,0,5,planes),(40,200,0,planes),(40,200,9,planes)]+[(40,200,8,planes[:i]+[0]+planes[i+1:]) for i in range(8)]:
 c.put(bitmap,struct.pack('>HHBBH8I',row,rows,0,depth,0,*ps));call(x,y,0xfffffffd);invalid+=1
assert matched>500 and blocked and unknown and upper_effect
print(json.dumps(dict(status='passed',native_pixel_comparisons=matched,blocked_pixels=blocked,unknown_bounds=unknown,nonzero_upper_word_cases=upper_effect,invalid_bitmaps=invalid,native_writes=0)));c.close()
