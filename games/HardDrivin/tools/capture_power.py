import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
from dissipation_model import trunc
from audit_forward_force import word
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',default='s4-power26.slave');p.add_argument('--profile',default='a500');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];entry=base+0xb696;leave=base+0xb6c0;vbl=base+0x3f2
 lines=[f'gdb break *{vbl:#x}',f'break *{entry:#x}',f'break *{leave:#x}','set $f=0','set $pending=0','while $f<500 || $pending!=0','continue',f'if $pc=={vbl:#x}','set $f=$f+1','end',f'if $pc=={entry:#x}','set $pending=1',f'printf "IN %d %d %d %d %u\\n",$f,*(signed char*){a4-0x66e4:#x},*(short*)$a2,*(short*)($a2+2),$sp','end',f'if $pc=={leave:#x} && $pending!=0','set $pending=0','printf "OUT %d %d %d %u\\n",$f,*(short*)($a5-14),(short)$d4,$sp','end','end','delete']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply);pending=None;count=0;repeated=0;previous=None;throttles=set();ratios=set()
 for tag,vals in re.findall(r'^(IN|OUT) ([-0-9 ]+)$',reply,re.M):
  r=list(map(int,vals.split()))
  if tag=='IN':assert pending is None;pending=r
  else:
   assert pending is not None;f,throttle,num,den,sp=pending
   first=word(trunc(throttle*450,100));result=word(trunc(first*den,num))
   assert r[1:]==[result,first,sp],(pending,r,first,result)
   key=(throttle,num,den);repeated+=key==previous;previous=key;count+=1;throttles.add(throttle);ratios.add((num,den));pending=None
 assert count and pending is None
 found=[]
 for bank,b in s.dump_banks('power-final'):
  i=b.find(b'HDPOWER1')
  if i>=0:found.append(struct.unpack_from('>IhHIhHII',b,i+8))
 assert len(found)==1;ratio,throttle,valid,result,first,pad,hits,misses=found[0]
 result=dict(passed=True,power_calls=count,consecutive_identical_inputs=repeated,cache_hits=hits,cache_misses=misses,throttle_values=sorted(throttles),ratio_pairs=sorted(ratios),stack_balanced=True)
 (out/'power-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
