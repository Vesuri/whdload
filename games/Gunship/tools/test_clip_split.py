"""Execute the assembled clip_split wrappers against stub native clippers.

Edges whose x or y span fits a signed word reach the native code once and
unchanged. Wider edges reach it as halves split at the floor midpoint, again
until every piece fits; the pieces join end to end in order. The edge wrapper
preserves what the native clipper preserves (d5-d6/a0-a6); the line wrapper
draws exactly the pieces the stub clipper accepts.
"""
from unicorn_b import *

def first_symbols(path):
 out={}
 for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',path.read_text(encoding='latin1'),re.M):out.setdefault(n,int(v,16))
 return out

H0=0x300000;LOG=0x310000;A5=0x320000
W=lambda v:struct.pack('>h',v)
REC=bytes.fromhex('2f09'+'22790031 0000'.replace(' ','')+'22ed0006'+'22ed000a'+'23c900310000'+'225f')
EDGE_STUB=bytes.fromhex('4e5e4cdf4f60')+REC+bytes.fromhex('4e75') # unlk; movem restore; record; rts
LINE_STUB=REC+bytes.fromhex('70004e75') # record; moveq #0 (accept); rts
def pieces(x1,y1,x2,y2):
 if -32768<=x2-x1<=32767 and -32768<=y2-y1<=32767:return [(x1,y1,x2,y2)]
 mx,my=(x1+x2)>>1,(y1+y2)>>1
 return pieces(x1,y1,mx,my)+pieces(mx,my,x2,y2)
CASES=[(10,20,300,40),(-160,118,480,-28),(-3978,915,29062,-3216),(29062,-3216,-3978,915),
 (-32768,0,32767,0),(0,-32768,0,32767),(-32277,32277,32277,-32277),(-1,-1,32766,-1),(-1,-1,32767,-1),(5,5,5,5)]
total=0
for name in ('Gunship','GunshipNTSC'):
 f=build/'release'/f'{name}.Slave';s=first_symbols(f.with_suffix('.lst'))
 for entry,stubs in (('clip_split_edge',{'GS0_86a0':EDGE_STUB}),('clip_split_line',{'GS0_82ec':LINE_STUB,'GS0_8542':bytes.fromhex('4e75')})):
  for (x1,y1,x2,y2) in CASES:
   c=CPU();c.put(base,bytes(BinFmt().load_image(str(f)).get_segments()[0].get_data()))
   c.put(base+s['clip_split_h0'],struct.pack('>I',H0))
   for k,code in stubs.items():c.put(H0+s[k],code)
   c.put(LOG,struct.pack('>I',LOG+4));c.put(A5+6,W(x1)+W(y1)+W(x2)+W(y2))
   regs={r:0x40000000+r*0x111 for r in list(range(1,8))+list(range(9,17))};regs[6]=A5
   for r,v in regs.items():c.rw(r,v)
   c.call(base+s[entry])
   n=(struct.unpack('>I',c.get(LOG,4))[0]-LOG-4)//8
   got=[struct.unpack('>4h',c.get(LOG+4+8*i,8)) for i in range(n)]
   assert got==pieces(x1,y1,x2,y2),(name,entry,(x1,y1,x2,y2),got)
   for a,b in zip(got,got[1:]):assert a[2:]==b[:2]
   if entry=='clip_split_edge':
    keep=[1,2,3,4,5,6,7,14,15] # a0-a6, d5-d6
    assert all(c.rr(r)==regs[r] for r in keep),(name,(x1,y1,x2,y2))
   assert c.rr(8)==0x8f004,(name,entry)
   c.close();total+=1
print(f'PASS {total} clip_split cases: pass-through, exact recursive midpoints, order, register preservation')
