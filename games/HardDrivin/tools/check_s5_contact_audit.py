import argparse,json,os,struct,shutil
from decimal import Decimal as D,getcontext
from capture_demo import ROOT
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='s4-contact-math-full');a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s5-audit-contact.slave',out/'slave.slave');s=Session(out,'a4000-040-25',out/'slave.slave',0x8520);s.env['CPU']='68040'
try:
 s.boot();got={}
 for bank,b in s.dump_banks('contact'):
  for sig,size in [(b'HDCWIDE1',1728),(b'HDCRESP1',1296),(b'HDCPROJ1',756),(b'HDCLIVE1',990),(b'HDCPITC1',2970)]:
   i=b.find(sig)
   if i>=0:assert sig not in got;got[sig]=b[i+8:i+8+size]
 getcontext().prec=60
 gain=[0]+[int(((1-(D(3)/4)**(D(n)/8))*65536).to_integral_value()) for n in range(1,9)]
 rate=[0]+[int(((1-(D(3)/4)**(D(n)/8))*8/D(n)*65536).to_integral_value()) for n in range(1,9)]
 errors=[-720,-361,-5,-1,0,1,5,361,720];response=[]
 for error in errors:
  for n in range(9):
   for half in range(2):
    if n==8:
     q=abs(error)//4*(-1 if error<0 else 1);r=q>>half;response.append((q*65536,r*65536))
    else:response.append((error*gain[n],(error*rate[n])>>half))
 assert list(struct.iter_unpack('>ii',got[b'HDCRESP1']))==response
 wide=[]
 for error in errors:
  for n in [9,15,31,63,127,255,327,328,655,32767,32768,65535]:
   g=int(((1-(D(3)/4)**(D(n)/8))*65536).to_integral_value());r=(g*8+n//2)//n
   exact=(1-(D(3)/4)**(D(n)/8))*8/D(n)*65536
   assert abs(D(r)-exact)<=D('0.5')+D(4)/n
   for half in range(2):wide.append((error*g,(error*r)>>half))
 assert list(struct.iter_unpack('>ii',got[b'HDCWIDE1']))==wide
 projection=[((error*65536+frac)*factor)//16384 for error in errors for frac in [-65535,0,65535] for factor in [-16384,-8192,-1,0,1,8192,16384]]
 assert [x[0] for x in struct.iter_unpack('>i',got[b'HDCPROJ1'])]==projection
 def trunc(n):return abs(n)//65536*(-1 if n<0 else 1)
 live=[]
 for raw in [-5,-1,0,1,5]:
  for n in range(9):
   error=-raw
   if n==8:
    q=abs(error)//4*(-1 if error<0 else 1);corr=q*65536;feedback=(q>>1)*65536
   else:corr=error*gain[n];feedback=(error*rate[n])>>1
   angle=100+trunc(corr);carry=corr-trunc(corr)*65536
   delta=feedback*n//8+carry;nextangle=angle+trunc(delta);nextcarry=delta-trunc(delta)*65536
   live.append((angle,trunc(feedback),feedback,carry,nextangle,nextcarry,0))
 assert list(struct.iter_unpack('>hhiihii',got[b'HDCLIVE1']))==live
 pitch=[]
 for raw in [-5,1,5]:
  for n in range(9):
   for factor in [-16384,-8192,0,8192,16384]:
    error=-raw
    if n==8:
     q=abs(error)//4*(-1 if error<0 else 1);corr=q*65536;feedback=(q>>1)*65536
    else:corr=error*gain[n];feedback=(error*rate[n])>>1
    projected=corr*factor//16384
    if n==8:projected=projected//65536*65536
    angle=100+trunc(projected);carry=projected-trunc(projected)*65536
    rate_projection=feedback*factor//16384
    if n==8:rate_projection=rate_projection//65536*65536
    delta=rate_projection*n//8+carry;nextangle=angle+trunc(delta);nextcarry=delta-trunc(delta)*65536
    pitch.append((angle,trunc(feedback),feedback,carry,nextangle,nextcarry,0))
 assert list(struct.iter_unpack('>hhiihii',got[b'HDCPITC1']))==pitch
 r=dict(passed=True,wide_contact_cases=len(wide),response_cases=len(response),projection_cases=len(projection),gain=gain,rate=rate,live_pitch_cases=len(pitch),live_roll_cases=len(live),live_hooks=True);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
finally:s.close()
