import argparse,json,os,shutil,struct
from capture_demo import ROOT
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='s4-position-wide');a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-position-wide.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();hits=[];projection=[];products=[]
 for bank,b in s.dump_banks('wide'):
  i=b.find(b'HDPOSW01')
  if i>=0:hits.append(b[i+8:i+8+8232])
  i=b.find(b'HDRPWID1')
  if i>=0:projection.append(b[i+8:i+8+8232])
  i=b.find(b'HDMULW01')
  if i>=0:products.append(b[i+8:i+8+432])
 assert len(hits)==1
 expected=[]
 for v in [-32768,-257,-1,0,1,257,32767]:
  for u in [-32768,-257,-1,0,1,257,32767]:
   for n in [9,15,31,255,32767,32768,65535]:
    for carry in [-127,0,127]:
     numerator=8*((8+n)*v-(8-n)*u)+carry;q=abs(numerator)//128*(-1 if numerator<0 else 1);expected.append((q,numerator-q*128))
 got=list(struct.iter_unpack('>ii',hits[0]));assert got==expected,[(i,x,y) for i,(x,y) in enumerate(zip(got,expected)) if x!=y][:10]
 projected=[]
 for v in [-86016,-65535,-1,0,1,65535,86016]:
  for u in [-86016,-65535,-1,0,1,65535,86016]:
   for n in [9,15,31,255,32767,32768,65535]:
    for carry in [-65535,0,65535]:
     full=((8+n)*v-(8-n)*u)//16+carry;q=abs(full)//65536*(-1 if full<0 else 1);projected.append((q,full-q*65536))
 assert len(projection)==1
 got_projection=list(struct.iter_unpack('>ii',projection[0]));assert got_projection==projected,[(i,x,y) for i,(x,y) in enumerate(zip(got_projection,projected)) if x!=y][:10]
 expected_products=[v*n for v in [-2147483648,-65537,-65536,-1,0,1,65535,65536,2147483647] for n in [0,1,8,32767,32768,65535]]
 assert len(products)==1 and [v[0] for v in struct.iter_unpack('>q',products[0])]==expected_products
 result=dict(product_cases=len(expected_products),projection_cases=len(projected),passed=True,cases=len(got),largest_displacement=max(abs(x[0]) for x in got));(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
