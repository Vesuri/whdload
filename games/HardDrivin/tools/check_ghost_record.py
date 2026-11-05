import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-ghost-record.slave');p.add_argument('--visits',type=int,default=160);p.add_argument('--native',action='store_true');p.add_argument('--delay',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x11664,a.delay);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits={};images=s.dump_banks('ghost')
 for bank,b in images:
  for sig in [b'HDGHREC1',b'HDDISP01',b'HDSCAL01']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 def read(addr,n):
  for bank,b in images:
   if bank<=addr and addr+n<=bank+len(b):return b[addr-bank:addr-bank+n]
  raise ValueError(hex(addr))
 assert len(hits)==3;gr=hits[b'HDGHREC1'];ds=hits[b'HDDISP01'];scalar=hits[b'HDSCAL01']-10;arena=struct.unpack('>I',read(a4+0x9644-65536,4))[0]
 def mem(addr,t='unsigned int'):return f'*({t}*){addr:#x}'
 def g(o,t='unsigned short'):return mem(a4+o-65536,t)
 (out/'records.bin').write_bytes(b'');lines=[f'gdb break *{base+0x8a9c:#x}',f'break *{base+0x116ac:#x}',f'break *{base+0x118a4:#x}','set $n=0','set $done=0',f'while $n<{a.visits} && $done==0','continue',f'if $pc=={base+0x118a4:#x}','set $done=1','end']
 expr=[mem(ds+8),mem(scalar,'unsigned short'),g(0xadde,'unsigned char'),g(0xe924,'unsigned int')+f'-{arena}',g(0xe922,'unsigned char')]+[mem(gr+off) for off in [0,4,8,12]]+[mem(gr+16,'unsigned short'),mem(gr+18,'unsigned short'),mem(gr+20,'unsigned char')]+[g(o) for o in [0x98f0,0x98f4,0x98f2,0x9944,0x9946,0x9948]]
 for tag,off in [('I',0x8a9c),('O',0x116ac)]:
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%u']*len(expr))+'\\n",'+','.join(expr),f'append binary memory {s.rel}/records.bin {arena:#x} {arena+3600:#x}']
  if tag=='O':lines+=['set $n=$n+1']
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 events=[(m[1],list(map(int,m[2].split()))) for m in re.finditer(r'^([IO]) ((?:\d+ ?)+)$',reply,re.M)];raw=(out/'records.bin').read_bytes();assert len(raw)==len(events)*3600 and len(events)%2==0
 def signed(x):return (x+32768)%65536-32768
 def interpolate(left,right,num,den):
  if num==den:return right[:]
  result=[]
  for i,(x,y) in enumerate(zip(left,right)):
   if i>=2:x=signed(x);y=signed(y)
   if i>=3:
    d=signed(y-x)
    if d>720:y-=1440
    if d< -720:y+=1440
   z=(x*(den-num)+y*num)//den
   if i>=3:
    if z>720:z-=1440
    if z< -720:z+=1440
   result.append(z&65535)
  return result
 age=0;emitted=0;previous=None;last_step=None;last_fields=0;nativecount=0;fractional=0;multi=0;eligible=0
 for ix in range(0,len(events),2):
  (ti,b),(to,v)=events[ix:ix+2];assert(ti,to)==('I','O')
  step,n,gate,ptr,phase,*_=b;pose=b[12:15]+[(-x)&65535 for x in b[15:18]];expected=bytearray(raw[ix*3600:(ix+1)*3600]);generated=0
  if gate:
   eligible+=1
   if a.native:
    nativecount+=1
    if nativecount%6==0:expected[ptr:ptr+12]=struct.pack('>6H',*pose);ptr=min(3588,ptr+12);emitted+=1;generated=1
    assert v[4]==nativecount%6
   else:
    before=age
    if previous is not None and step==last_step+1:age+=last_fields
    while 40+48*emitted<=age:
     when=40+48*emitted;assert previous is not None and age>before
     sample=interpolate(previous,pose,when-before,age-before);expected[ptr:ptr+12]=struct.pack('>6H',*sample);ptr=min(3588,ptr+12);emitted+=1;generated+=1;fractional+=when!=age
    assert v[3]==min(3588,emitted*12)
    assert (v[4],v[7],v[8],v[9],v[10],v[11])==(((age+8)%48)//8,age,emitted,(age+8)%48,n,255),(ix,b,v,age,emitted)
    previous=pose;last_step=step;last_fields=n
  assert v[3]==ptr,(ix,b,v,ptr)
  actual=raw[(ix+1)*3600:(ix+2)*3600];assert actual==expected,(ix,next(j for j,(x,y) in enumerate(zip(actual,expected)) if x!=y),b,v)
  multi+=generated>1
 result=dict(passed=True,visits=len(events)//2,eligible_visits=eligible,age_fields=age,emitted=emitted,fractional_samples=fractional,multiple_sample_visits=multi,native=a.native,profile=a.profile);(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
