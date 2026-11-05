"""Observe the native menu cursor sample and automatic/manual selection."""
import argparse,os
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--profile',default='a500-fast');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);s=Session(out,a.profile,ROOT/'tmp/build'/a.slave,0x8520);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4']
 sites=[0x6d46,0x6f78,0x6f94,0x6fae]
 lines=[f'gdb break *{base+0x3f2:#x}']+[f'break *{base+x:#x}' for x in sites]+['set $f=0','set $done=0','while $f<1800 && $done==0','continue',f'if $pc=={base+0x3f2:#x}','set $f=$f+1','else']
 expr=['$pc-'+str(base),'$f',f'*(short*){a4-0x6a06:#x}',f'*(short*){a4-0x69ec:#x}',f'*(unsigned short*){a4-0x6a0a:#x}','$d0',f'*(unsigned char*){a4-0x66c2:#x}']
 lines+=['printf "MENU %x %d %d %d %u %d %u\\n",'+','.join(expr),'end',f'if $pc=={base+0x6fae:#x}','set $done=1','end','end','delete']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply);print('\n'.join(x for x in reply.splitlines() if x.startswith('MENU ')))
finally:s.close()
