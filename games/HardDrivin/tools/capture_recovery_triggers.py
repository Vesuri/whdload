"""Observe native recovery triggers and their state; no guest writes."""
import argparse,json,os
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--custom1',type=int,default=1);p.add_argument('--fields',type=int,default=1250);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);s=Session(out,'a500',ROOT/'tmp/build'/a.slave,0x10ed4);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 s.boot();code=s.layout['code_base'];a4=s.layout['a4']
 def g(off,t='unsigned char'):return f'*({t}*){a4+off-65536:#x}'
 offsets=[0x7c78,0x105f4,0x10e92,0x108b8,0x10af8]
 lines=[f'gdb break *{code+0x3f2:#x}']+[f'break *{code+x:#x}' for x in offsets]+['set $f=0',f'while $f<{a.fields}','continue',f'if $pc=={code+0x3f2:#x}','set $f=$f+1','else']
 expr=['$pc-'+str(code),'$f',g(0x9605),g(0x8cec),g(0x9606),g(0xadd7),g(0xe94a),g(0x9928,'short'),g(0x9790,'unsigned int'),g(0xadd8,'unsigned int')]
 lines += ['printf "REC %x %d %d %d %d %d %d %d %x %x\\n",'+','.join(expr),'end','end','delete']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply);print('\n'.join(x for x in reply.splitlines() if x.startswith('REC ')))
finally:s.close()
