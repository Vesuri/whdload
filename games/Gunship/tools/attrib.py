#!/usr/bin/env python3
"""Attribute a flight_profile window by context, call stack and library call: attrib.py RUN MEMDIR OUT.pkl

RUN holds chunk_NNN.bin (consecutive); MEMDIR is dump_start.py output. Contexts by SP: the game
task's stack and the supervisor stack (interrupts, exec dispatcher, STOP). Task call stacks are
rebuilt from JSR/BSR (a frame per call, popped when SP rises above it); a call into a library
jump table is named lib:-LVO. Supervisor time goes to the handler entered after each exception
gap. Saves counters for report_attrib.py.
"""
import collections,glob,os,pickle,struct,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
GAP=0x7fffffff
run,memdir,outp=sys.argv[1:4]
fast=open(os.path.join(memdir,'fast.bin'),'rb').read();chip=open(os.path.join(memdir,'chip.bin'),'rb').read()
def rd(a,n):
    if 0x200000<=a<0xa00000-n:return fast[a-0x200000:a-0x200000+n]
    if a<0x80000-n:return chip[a:a+n]
    return b'\0'*n
def w16(a):return struct.unpack('>H',rd(a,2))[0]
def l32(a):return struct.unpack('>I',rd(a,4))[0]
def cstr(a):
    b=rd(a,40);return b.split(b'\0')[0].decode('latin-1')
libname={}
def lib(base):
    if base not in libname:
        n=cstr(l32(base+10)) if base else '';libname[base]=n.replace('.library','').replace('.device','.dev') or f'{base:#x}'
    return libname[base]
def is_call(pc):
    op=w16(pc)
    if op&0xff00==0x6100:return True                       # bsr
    if op&0xffc0==0x4e80:return (op&0x38)>>3 in (2,5,6,7)  # jsr (an)/d16(an)/d8(an,xn)/abs/pc
    return False
SUP=lambda sp:0x9f0000<=sp<0x9f8000
# Counters
ctx=collections.Counter()                  # context -> cycles
selfc=collections.Counter()                # pc -> cycles (task context)
incl=collections.Counter()                 # frame name -> inclusive cycles (task)
paths=collections.Counter()                # tuple(frames) -> self cycles (task)
calls=collections.Counter()                # frame name -> entries
sup=collections.Counter()                  # handler entry -> cycles
supself=collections.Counter()              # pc -> cycles (supervisor)
supn=collections.Counter()                 # handler entry -> entries
perfield=[]
stack=[];handler=None;prev=None;prev_sp=None;prev_a6=0
files=sorted(glob.glob(os.path.join(run,'chunk_*.bin')))
for fn in files:
    t=barto.load(fn)
    for f in t.fields:
        fc=collections.Counter()
        for pc,cost,regs in t.instructions(f):
            if pc is None:ctx['nopc']+=cost;fc['nopc']+=cost;continue
            if pc==GAP:ctx['exception']+=cost;fc['exception']+=cost;prev=GAP;continue
            sp=regs[15]
            if SUP(sp):
                if prev==GAP or handler is None:handler=pc;supn[pc]+=1
                ctx['supervisor']+=cost;fc['supervisor']+=cost
                sup[handler]+=cost;supself[pc]+=cost
                if pc==0x935f90:fc['stop']+=cost
                prev=pc;continue
            handler=None
            while stack and sp>stack[-1][1]:stack.pop()
            if prev is not None and prev!=GAP and prev_sp is not None and not SUP(prev_sp) and sp==prev_sp-4 and is_call(prev):
                op=w16(prev)
                if op==0x4eae:name=f'{lib(prev_a6)}:{struct.unpack(">h",rd(prev+2,2))[0]}'
                else:name=pc
                stack.append((name,sp));calls[name]+=1
            ctx['task']+=cost;fc['task']+=cost;selfc[pc]+=cost
            key=tuple(n for n,_ in stack);paths[key]+=cost
            for n in set(key):incl[n]+=cost
            prev=pc;prev_sp=sp;prev_a6=regs[14]
        perfield.append(dict(fc,cycles=f.cycles))
    print(fn,len(stack),flush=True)
pickle.dump(dict(ctx=ctx,selfc=selfc,incl=incl,paths=paths,calls=calls,sup=sup,supself=supself,supn=supn,perfield=perfield,libname=libname),open(outp,'wb'))
