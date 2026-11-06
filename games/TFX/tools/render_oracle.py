"""Independent pixel-by-pixel model; no C2P bit permutation or guest fill code."""
import struct
MASK=0xffffffff
def expected_buffer(c):
 buf=bytearray();v=0xa55a6996
 for i in range(16016):
  buf+=struct.pack('>I',v);v=(((v<<3)|(v>>29))+0x13ab)&MASK
 if c is None:return buf
 def plot(x,y,color):
  assert 0<=x<320 and 0<=y<200,(x,y)
  for plane in range(8):
   o=32+plane*8000+y*40+x//8;mask=1<<(7-x%8)
   if color&(1<<plane):buf[o]|=mask
   else:buf[o]&=255^mask
 def div(x,y):return abs(x)//y*(-1 if x<0 else 1)
 if c['kind'] in ['box','clip']:
  if c['y0']<200:
   for y in range(c['y0'],min(199,c['y1'])+1):
    for x in range(c['x0'],c['x1']+1):plot(x,y,c['color'])
 elif c['kind']=='normal':
  left,right=c['left'],c['right']
  for j in range(c['height']):
   for x in range(left>>16,(right>>16)+1):plot(x,c['y']+j,c['color'])
   left+=c['slope'];right-=c['slope']
 else:
  rows=c['rows'];stride=4 if c['kind']=='gouraud' else 6
  tex=b''.join(struct.pack('>I',(0x00010203+i*0x04040404)&MASK) for i in range(16384))
  for j in range(c['height']):
   row=rows[j*stride:(j+1)*stride];l,rr=row[0]>>16,row[1]>>16
   if rr<l:break
   n=rr-l+1
   if c['kind']=='gouraud':
    step=div(row[3]-row[2],n);v=row[2]+(step>>1)
    for x in range(l,rr+1):plot(x,c['y']-j,(v>>16)&255);v+=step
   else:
    lu,lv,ru,rv=[v>>1 for v in row[2:]];du,dv=div(ru-lu,n),div(rv-lv,n);u,v=lu+(du>>1),lv+(dv>>1)
    for x in range(l,rr+1):
     color=tex[(u>>20)+((v>>20)<<8)]
     if color:plot(x,c['y']-j,color)
     u+=du;v+=dv
 return buf
