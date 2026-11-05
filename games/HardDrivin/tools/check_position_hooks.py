import json,os,struct,shutil
from capture_demo import ROOT,command
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s4-position-small-hooks';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-position-small.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits=[]
 for bank,b in s.dump_banks('positions'):
  i=b.find(b'HDPOSST1')
  if i>=0:hits.append(bank+i+8)
 assert len(hits)==1;st=hits[0]
 lines=[f'gdb break *{base+0xb578:#x}',f'break *{base+0xb596:#x}',f'break *{base+0xcdb0:#x}','set $n=0','while $n<120','continue',f'if $pc=={base+0xcdb0:#x}','set $n=$n+1','end']
 for label,site in [('IN',0xb578),('OUT',0xb596)]:
  lines+=[f'if $pc=={base+site:#x}']
  for axis in range(3):
   expr=[f'*(long*){a4+0x98fc-65536+axis*4:#x}',f'*(short*){a4+0x991e-65536+axis*2:#x}',f'*(short*){st+axis*2:#x}',f'*(long*){st+8+axis*4:#x}']
   lines+=[f'printf "{label} {axis} %d %d %d %d\\n",'+','.join(expr)]
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 pending={};count=0;fractional=0;errors=[]
 for line in reply.splitlines():
  if line.startswith('IN '):
   _,axis,pos,v,u,carry=line.split();axis,pos,v,u,carry=map(int,[axis,pos,v,u,carry]);n=8*(9*v-7*u)+carry;q=abs(n)//128*(-1 if n<0 else 1);pending[axis]=(pos+q,n-128*q)
  elif line.startswith('OUT '):
   _,axis,pos,v,u,carry=line.split();axis,pos,carry=map(int,[axis,pos,carry]);exp=pending.pop(axis,None)
   # Crash entry goes directly to this boundary without ordinary integration.
   if exp is None:continue
   count+=1;fractional+=carry!=0
   if (pos,carry)!=exp:errors.append(dict(line=line,expected=exp))
 assert count>100 and fractional>0 and not pending
 r=dict(passed=not errors,axis_updates=count,fractional_results=fractional,errors=errors);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert r['passed']
finally:s.close()
