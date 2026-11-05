import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
from audit_forward_force import native_sqrt
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',default='s4-sqrt26.slave');p.add_argument('--profile',default='a500');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];entry=base+0xb854;leave=base+0xb85c;vbl=base+0x3f2
 lines=[f'gdb break *{vbl:#x}',f'break *{entry:#x}',f'break *{leave:#x}','set $f=0','set $pending=0','while $f<500 || $pending!=0','continue',f'if $pc=={vbl:#x}','set $f=$f+1','end',f'if $pc=={entry:#x}','set $pending=1','printf "IN %d %u %u\\n",$f,$d0,$sp','end',f'if $pc=={leave:#x}','set $pending=0','printf "OUT %d %u %u\\n",$f,$d0,$sp','end','end','delete']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply);pending=None;count=0;repeated=0;previous=None
 for tag,vals in re.findall(r'^(IN|OUT) ([0-9 ]+)$',reply,re.M):
  r=list(map(int,vals.split()))
  if tag=='IN':assert pending is None;pending=r
  else:
   assert pending is not None;f,key,sp=pending
   assert r[1]==native_sqrt(key) and r[2]==sp,(pending,r)
   repeated+=key==previous;previous=key;count+=1;pending=None
 assert count and pending is None
 found=[]
 for bank,b in s.dump_banks('sqrt-final'):
  i=b.find(b'HDSQRT01')
  if i>=0:found.append(struct.unpack_from('>IIHHII',b,i+8))
 assert len(found)==1;key,value,valid,pad,hits,misses=found[0]
 result=dict(passed=True,root_calls=count,consecutive_identical_operands=repeated,cache_hits=hits,cache_misses=misses,final_key=key,final_value=value,stack_balanced=True)
 (out/'sqrt-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
