"""Independent Decimal oracle (80 digits), not the guest implementation."""
from decimal import Decimal,localcontext
import struct
PI=Decimal('3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628')
def extended(h):
 w,m=struct.unpack('>IQ',bytes.fromhex(h));e=(w>>16)&32767
 if e==32767:return Decimal('NaN')
 with localcontext() as c:
  c.prec=90
  return (-1 if w>>31 else 1)*Decimal(m)*Decimal(2)**((e or 1)-16383-63)
def atan(x):
 if not x:return x
 sign=-1 if x<0 else 1;x=abs(x);inv=x>1
 if inv:x=1/x
 # Eight half-angle reductions, independent series termination.
 for _ in range(8):x=x/(1+(1+x*x).sqrt())
 t=x;s=x;n=1
 while True:
  t*=-x*x;n+=2;v=t/n
  if abs(v)<Decimal('1e-85'):break
  s+=v
 s*=256
 if inv:s=PI/2-s
 return sign*s
def oracle(op,x):
 with localcontext() as c:
  c.prec=80
  if op in ('atan','atan2'):return +atan(x)
  if op=='asin':
   if abs(x)>1:return Decimal('NaN')
   if abs(x)==1:return x*PI/2
   return +atan(x/(1-x*x).sqrt())
  x=x%(2*PI)
  if x>PI:x-=2*PI
  if x< -PI:x+=2*PI
  sin=x;cos=Decimal(1);a=x;b=Decimal(1);n=0
  while True:
   n+=1;a*= -x*x/((2*n)*(2*n+1));b*= -x*x/((2*n-1)*(2*n));sin+=a;cos+=b
   if max(abs(a),abs(b))<Decimal('1e-85'):break
  return sin if op=='sin' else cos if op=='cos' else sin/cos
