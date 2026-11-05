import json,os,shutil
from capture_demo import ROOT,command
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s4-projection-small';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-projection-small.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits={}
 for bank,b in s.dump_banks('projection'):
  for sig in [b'HDVPROJ1',b'HDPOSST1',b'HDSCAL01']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 assert len(hits)==3;vs=hits[b'HDVPROJ1'];ps=hits[b'HDPOSST1'];ss=hits[b'HDSCAL01']
 def g(off,typ='short'):return f'*({typ}*){a4+off-65536:#x}'
 lines=[f'gdb break *{base+0xb578:#x}',f'break *{base+0xb596:#x}',f'break *{base+0xcdb0:#x}','set $n=0','while $n<120','continue',f'if $pc=={base+0xcdb0:#x}','set $n=$n+1','end',f'if $pc=={base+0xb578:#x}']
 expr=[f'*(short*){ss:#x}',f'*(short*){ss+2:#x}',g(0x9928),g(0xaf31,'unsigned char')]+[g(x) for x in [0x9448,0x944a,0x944c,0x944e]]
 lines+=['printf "PARAM '+('%d '*8).strip()+'\\n",'+','.join(expr),'end']
 for label,site in [('IN',0xb578),('OUT',0xb596)]:
  lines+=[f'if $pc=={base+site:#x}']
  for axis in range(3):
   expr=[g(0x98fc+axis*4,'long'),g(0x991e+axis*2),f'*(short*){ps+axis*2:#x}',f'*(long*){ps+8+axis*4:#x}',f'*(long*){vs+axis*4:#x}',f'*(long*){vs+12+axis*4:#x}',f'*(long*){vs+24+axis*4:#x}']
   lines+=[f'printf "{label} {axis} '+('%d '*7).strip()+'\\n",'+','.join(expr)]
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 def trunc(n,d):return abs(n)//d*(-1 if n<0 else 1)
 pending={};count=0;fractional=0;errors=[];extra_units=0
 for line in reply.splitlines():
  if line.startswith('PARAM '):
   carry,last,v,spin,sy,cy,sp,cp=map(int,line.split()[1:])
   if v!=last:carry=0
   speed=carry*12288;along=speed*cp//16384;projected=[along*sy//16384,speed*sp//16384,along*cy//16384]
  elif line.startswith('IN '):
   axis,pos,v,u,carry,current,previous,fine=map(int,line.split()[1:]);new=current if spin else projected[axis]
   native=8*(9*v-7*u)+carry;q=trunc(native,128)
   full=(9*new-7*previous)//16+fine;extra=trunc(full,65536)
   pending[axis]=(pos+q+extra,native-q*128,new,full-extra*65536);fractional+=new!=0;extra_units+=abs(extra)
  elif line.startswith('OUT '):
   axis,pos,v,u,carry,current,previous,fine=map(int,line.split()[1:]);expected=pending.pop(axis,None)
   if expected is None:continue
   got=(pos,carry,current,fine);count+=1
   if got!=expected:errors.append(dict(line=line,expected=expected))
 r=dict(passed=not errors and count==360 and fractional>0,axis_updates=count,fractional_projection_updates=fractional,extra_position_units=extra_units,errors=errors);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert r['passed']
finally:s.close()
