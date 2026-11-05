"""Models of the original 68000 W2/W3 loops, including word wrap and sentinels."""
import struct
s16=lambda x: ((x+0x8000)&0xffff)-0x8000
s32=lambda x: ((x+0x80000000)&0xffffffff)-0x80000000

def clip(x,y,rect):
 xmin,xmax,ymin,ymax=rect
 return (1 if y<ymin else 2 if y>ymax else 0)+(4 if x<xmin else 8 if x>xmax else 0)

def rotate_parent(parent,rec,matrix,mode):
 # Original cases 0/invalid copy, 7 negates; 1,2,4 add; 3,5,6 subtract.
 if mode==7:return [s16(-x) for x in parent]
 cases={1:(0,1),2:(1,1),3:(2,-1),4:(2,1),5:(1,-1),6:(0,-1)}
 if mode not in cases:return list(parent)
 row,sign=cases[mode];v=s16(rec[row]*2)
 return [s16((v*matrix[row*3+j]>>14)+sign*parent[j]) for j in range(3)]

def transform(rec,matrix):
 return [s16(s32(sum(rec[k]*matrix[k*3+j] for k in range(3)))>>14) for j in range(3)]

def project(v,scales):
 x,y,z=v;sx,sy,cy,cx=scales
 if z<=0:return [-32768,-32768]
 def one(v,m,center,negative_sentinel,positive_sentinel,flip):
  neg=v<0;mag=(-v if neg else v)&0xffff;product=mag*m
  threshold=s16(2*(product>>16)+bool(product&0x8000))
  if z<=threshold:return s16(negative_sentinel if neg else positive_sentinel)
  q=product//z
  # DIVU overflow leaves the dividend unchanged; the game's threshold normally prevents it.
  if q>65535:q=product&0xffff
  q=s16(-q if neg else q)
  return s16((-q if flip else q)+center)
 return [one(x,sx,cx,0x8300,0x7d00,False),one(y,sy,cy,0x2000,0x8300,True)]

def model(kind,frame,a5,globals_,read):
 f=bytearray(frame);origin=a5-len(f)
 def u8(o):return f[len(f)+o]
 def w(o):return struct.unpack_from('>h',f,len(f)+o)[0]
 def l(o):return struct.unpack_from('>I',f,len(f)+o)[0]
 def put(o,fmt,*values):struct.pack_into('>'+fmt,f,len(f)+o,*values)
 def gw(o):return struct.unpack_from('>h',globals_,0x7ffe+o)[0]
 n=globals_[0x7ffe-0x19b4];rect=tuple(gw(-0x2b38+i*2) for i in range(4))
 changes={}
 if kind=='vertices':
  put(-9,'B',15);put(-0x84,'H',1);put(-0x86,'H',0);put(-0x12,'I',l(-0xe));put(-8,'H',0)
  matrix=[w(-0x70+i*2) for i in range(9)]
  for i in range(n):
   v=read(l(-0x12),1)[0];put(-0x12,'I',l(-0x12)+1);put(-2,'H',v)
   put(-0x5a+4*i,'I',a5-0xbc2+4*v)
   st=u8(-0x19f+v)
   if st==255:
    rec=read(l(-0x16)+8*v,8);f[len(f)-0x1e:len(f)-0x16]=rec
    coords=list(struct.unpack('>3h',rec[:6]));mode,parent=rec[6:]
    if mode and u8(-0x19f+parent)!=255:
     if gw(-0x199a):
      coords=[v>>1 for v in coords];put(-0x1e,'3h',*coords)
     view=rotate_parent([w(-0x7c6+parent*6+j*2) for j in range(3)],coords,matrix,mode)
    else:
     if gw(-0x199a):coords=[v>>1 for v in coords]
     put(-0x1ba,'3h',*coords);view=transform(coords,matrix)
    put(-0x1c0,'3h',*view);put(-0x7c6+v*6,'3h',*view)
    view[2]=s16(view[2]+w(-0x1c8));put(-0x1bc,'h',view[2])
    if view[2]<12:
     put(-0x19f+v,'B',1);put(-0x86,'H',1);put(-8,'H',i+1);continue
    view[0]=s16(view[0]+w(-0x1cc));view[1]=s16(view[1]+w(-0x1ca));put(-0x1c0,'3h',*view)
    out=project(view,[gw(-0x389a)&0xffff,gw(-0x3898)&0xffff,gw(-0x3896),gw(-0x3894)])
    put(-0xbc2+4*v,'2h',*out);put(-0x19f+v,'B',0);st=0
   if st==0:
    put(-0x84,'H',0)
    if u8(-9):put(-9,'B',u8(-9)&clip(w(-0xbc2+4*v),w(-0xbc0+4*v),rect))
   elif st==1:put(-0x86,'H',1)
   put(-8,'H',i+1)
 else:
  for i in range(n):
   v=read(l(-0x12),1)[0];put(-0x12,'I',l(-0x12)+1);put(-0x98,'H',v)
   put(-0x1a4,'I',(l(-0x1a4)+w(-0x7c6+6*v+4))&0xffffffff)
   at=l(-0x5a+4*i);xy=bytes(f[at-origin:at-origin+4]);assert len(xy)==4
   changes[l(-0xbc6)]=xy;put(-0xbc6,'I',l(-0xbc6)+4)
   if u8(-9):put(-9,'B',u8(-9)&clip(*struct.unpack('>2h',xy),rect))
 return bytes(f),changes
