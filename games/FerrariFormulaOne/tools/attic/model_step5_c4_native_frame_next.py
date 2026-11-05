from pathlib import Path
import json,random
r=Path(__file__).resolve().parents[1];mask=0xffffffff
sg=lambda x:x if x<0x80000000 else x-2**32
word=lambda x:x<32768 or x>=0xffff8000
def native(a,b,x):
 if not a:return 0,x|4
 aa=abs(sg(a))&mask
 if not b:return 0,(16 if a&0x80000000 else x)|4
 bb=abs(sg(b))&mask
 low=(aa&65535)*(bb&65535)
 cross1=((aa>>16)*(bb&65535)<<16)&mask
 cross2=((aa&65535)*(bb>>16)<<16)&mask
 partial=(low+cross1)&mask;total=partial+cross2;product=total&mask
 if (a^b)&0x80000000:
  result=(-product)&mask
  flags=(17 if product else 4)|(8 if result&0x80000000 else 0)|(2 if product==0x80000000 else 0)
  return result,flags
 return product,(16 if total>mask else 0)|(4 if a==b else 0)
def fast(a,b,x):
 if a<=65535 and b<=65535:
  if not a or not b:return 0,x|4
  return (a*b)&mask,4 if a==b else 0
 if a==8 and 65535<b<0x80000000:return (8*b)&mask,0
 if word(a) and word(b):
  if not a:return 0,x|4
  if not b:return 0,20 # A is negative; nonnegative A used unsigned path.
  p=sg(a)*sg(b)
  return p&mask,4 if a==b else 25 if p<0 else 0
 return native(a,b,x)
count=0
def check(a,b):
 global count
 for x in (0,16):
  assert native(a,b,x)==fast(a,b,x),(hex(a),hex(b),x,native(a,b,x),fast(a,b,x));count+=1
for a in (-32768,-1,0,1,8,32767,32768,65535):
 for b in range(-32768,32768):check(a&mask,b&mask)
rng=random.Random(0xc4e)
for _ in range(50000):
 check(rng.getrandbits(32),rng.getrandbits(32));check(8,rng.randrange(65536,0x80000000))
p=r/'manifest/step5-c4-native-frame-next-model.json';p.write_text(json.dumps(dict(status='passed',comparisons=count,scope='Planning-only Python model of native low32 multiply and XNZVC; each original X bit, full signed-word sweeps at eight A boundaries, full-width random inputs and guarded 8*positive-long cases. Assembly/native guest oracle remains required.'),indent=2)+'\n');print(count,'model comparisons passed')
