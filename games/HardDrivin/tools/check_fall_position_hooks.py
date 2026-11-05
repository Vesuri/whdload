import argparse,json,os,struct,shutil
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--profile',default='a500');p.add_argument('--updates',type=int,default=200);a=p.parse_args()
os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits=[]
 for bank,b in s.dump_banks('positions'):
  i=b.find(b'HDMOTN01')
  if i>=0:hits.append(bank+i+8)
 assert len(hits)==1;st=hits[0]
 pos_hits=[]
 for bank,b in s.dump_banks('fall-positions'):
  i=b.find(b'HDPOSST1')
  if i>=0:pos_hits.append(bank+i+8)
 assert len(pos_hits)==1;pos_st=pos_hits[0]
 scalar_hits=[]
 for bank,b in s.dump_banks('fall-scalar'):
  i=b.find(b'HDSCAL01')
  if i>=0:scalar_hits.append(bank+i-2)
 assert len(scalar_hits)==1;scalar=scalar_hits[0]
 drive_hits=[]
 for bank,b in s.dump_banks('fall-drive'):
  i=b.find(b'HDDRIVE1')
  if i>=0:drive_hits.append(bank+i+8)
 assert len(drive_hits)==1;drive=drive_hits[0]
 lines=[f'gdb break *{base+0xb5f2:#x}',f'break *{base+0xb5fc:#x}','set $n=0',f'while $n<{a.updates}','continue',f'if $pc=={base+0xb5f2:#x}']
 expr=[f'*(long*){a4+0x9900-65536:#x}',f'*(short*){a4+0x990e-65536:#x}',f'*(short*){st+18:#x}',f'*(short*){st+20:#x}',f'*(short*){st+30:#x}',f'*(long*){pos_st+12:#x}',f'*(unsigned short*){scalar:#x}',f'*(unsigned char*){a4+0x9910-65536:#x}',f'*(unsigned short*){drive+6:#x}',f'*(unsigned short*){drive:#x}',f'*(unsigned int*){drive+12:#x}']
 lines+=[f'printf "IN %d %d %d %d %d %d %d %d %d %d %d\\n",'+','.join(expr),'end',f'if $pc=={base+0xb5fc:#x}',f'printf "OUT %d %d\\n",*(long*){a4+0x9900-65536:#x},*(long*){pos_st+12:#x}','set $n=$n+1','end','end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 pending=None;count=0;nonzero=0;errors=[];intervals=set();masks={};wide=0;reference_fall=0;reference_partial=0;serials=set()
 for line in reply.splitlines():
  if line.startswith('IN '):
   assert pending is None
   pos,v,frac,last,acc,carry,fields,mask,active,original,serial=map(int,line.split()[1:]);nonzero+=v!=0;intervals.add(fields);masks[mask]=masks.get(mask,0)+1;wide+=fields>8
   assert serial not in serials;serials.add(serial)
   assert fields==original
   reference_fall+=active==2 and v!=0
   reference_partial+=active==2 and mask not in (0,15)
   if v!=last:frac=acc=0
   n=-16*v*fields-2*frac*fields+acc*fields*(8-fields)+carry;q=abs(n)//128*(-1 if n<0 else 1);pending=(((pos+q+2**31)%2**32)-2**31,n-128*q)
  elif line.startswith('OUT '):
   got=tuple(map(int,line.split()[1:]));count+=1
   if got!=pending:errors.append(dict(line=line,expected=pending))
   pending=None
 assert count==a.updates and nonzero>0 and not pending
 r=dict(passed=not errors,updates=count,nonzero_fall_updates=nonzero,intervals=sorted(intervals),contact_masks=masks,wide_updates=wide,reference_fall_updates=reference_fall,reference_partial_updates=reference_partial,errors=errors);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert r['passed']
finally:s.close()
