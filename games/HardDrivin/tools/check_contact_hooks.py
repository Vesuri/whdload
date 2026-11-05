import json,os,shutil
from capture_demo import ROOT,command
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s4-contact-tape-trace';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-contact-trace.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];sites=[('roll',0xccfa,0xcd18,0x9914),('pitch',0xcd2e,0xcd4e,0x9916),('rear',0xcd6e,0xcd80,0x9916)]
 hits=[]
 for bank,b in s.dump_banks('contact-trace'):
  i=b.find(b'HDCRATE1')
  if i>=0:hits.append(bank+i+8)
 assert len(hits)==1;st=hits[0]
 addresses=[base+x for _,start,end,_ in sites for x in [start,end]]+[base+0xcdb0]
 lines=['gdb break *'+hex(addresses[0])]+['break *'+hex(x) for x in addresses[1:]]+['set $n=0','while $n<400','continue',f'if $pc=={base+0xcdb0:#x}','set $n=$n+1','end']
 for name,start,end,g in sites:
  lines += [f'if $pc=={base+start:#x}',f'printf "IN {name} %d\\n",(short)$d0','end',f'if $pc=={base+end:#x}',f'printf "OUT {name} %d %d\\n",*(short*){a4+g-65536:#x},*(short*){st+(6 if name=="roll" else 14):#x}','end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply);pending={};counts={k:0 for k,*_ in sites};nonzero={k:0 for k,*_ in sites};errors=[]
 for line in reply.splitlines():
  if line.startswith('IN '):
   _,k,raw=line.split();e=-int(raw);q=abs(e)//4*(-1 if e<0 else 1);pending[k]=q if k=='rear' else q//2
  elif line.startswith('OUT '):
   _,k,v,recorded=line.split()
   if k not in pending:continue
   got=int(v);previous=pending.pop(k);e=-int(recorded);q=abs(e)//4*(-1 if e<0 else 1);expected=q if k=='rear' else q//2;counts[k]+=1;nonzero[k]+=got!=0
   if got!=expected:errors.append(dict(line=line,expected=expected))
 r=dict(passed=not errors and sum(counts.values())>0,counts=counts,nonzero_rates=nonzero,errors=errors);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert r['passed']
finally:s.close()
