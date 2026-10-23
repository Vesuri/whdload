#!/usr/bin/env python3
"""A3 dynamic effective-address inventory: state_access.py TRACE FAST_DUMP OUT.json.
All paths in tmp/. Requires Capstone 5. Separates the main task by stack because
KickEmu virtualizes SR; the trace CCR alone does not identify interrupt context.
Reports read/write intersections as candidates, not evidence of data dependence.
"""
import sys,json,struct,collections
from pathlib import Path
from race_profile import barto,image,locate,game_hunks
from state_diff import spans, scratch, digest
from slave_inputs import verify
verify()
from capstone import *
from capstone.m68k import *
c=Cs(CS_ARCH_M68K,CS_MODE_M68K_000|CS_MODE_BIG_ENDIAN);c.detail=True
trace=scratch(sys.argv[1]);fast=scratch(sys.argv[2]);out=scratch(sys.argv[3])
t=barto.load(str(trace));mem=image(t.chip,fast.read_bytes(),t.slow);found=locate(mem,game_hunks());h0,h2=found[0][0],found[2][0];nxt=lambda h:struct.unpack_from('>I',mem,h-4)[0]*4+4
bases=[h0,nxt(h0),h2,nxt(h2)];sizes=[0x44a54,0x2a940,0x41c70,0x14f84]
def label(a):
 for h,(b,z) in enumerate(zip(bases,sizes)):
  if b<=a<b+z:return f'h{h}+{a-b:05x}'
 return f'other+{a:x}'
def region(a):
 for h,(b,z) in enumerate(zip(bases,sizes)):
  if b<=a<b+z:return h,a-b
 return 4,a
cache={};unknown=set();result={};reads={};writes={};counts=collections.Counter();owner=None;osp=None;ret=None
ranges=[(h0+0x3c944,h0+0x3ca56),(h0+0x3cc8e,h0+0x3cd0c),(h0+0x3c5c6,h0+0x3c66a)]

def reg(r,n):
 if 1<=n<=16:return r[n-1]
 raise ValueError('register '+str(n))
def signed(v,b):return (v&((1<<(b-1))-1))-(v&(1<<(b-1)))
def ea(o,r,pc,size):
 am=o.address_mode
 if am in (16,17):return o.imm&0xffffff
 if am in (3,4):return reg(r,o.reg)&0xffffff
 if am==5:return (reg(r,o.reg)-(2 if size==1 and o.reg==16 else size))&0xffffff
 if am==6:return (reg(r,o.mem.base_reg)+o.mem.disp)&0xffffff
 if am in (7,8,12,13):
  base=pc+2 if am in (12,13) else reg(r,o.mem.base_reg)
  ix=reg(r,o.mem.index_reg);ix=signed(ix,32 if o.mem.index_size else 16)
  return (base+o.mem.disp+ix*(o.mem.scale or 1))&0xffffff
 if am==11:return (pc+2+o.mem.disp)&0xffffff
 raise ValueError('mode '+str(am))
for field in t.fields:
 for pc,cy,r in t.instructions(field):
  if pc is None or pc==0x7fffffff:continue
  if r[16]&0x2000:continue # interrupt/system context; never attribute to a live call
  if pc==ret and r[15]==osp:owner=None;ret=None
  if pc not in cache:
   i=next(c.disasm(mem[pc:pc+24],pc,count=1),None)
   cache[pc]=i
  i=cache[pc]
  if i is None:unknown.add((label(pc),'decode'));continue
  op=i.mnemonic.split('.')[0]
  if any(a<=pc<b for a,b in ranges) and op=='jsr':
   owner=label(pc);osp=r[15];ret=pc+i.size;counts[owner]+=1
  if owner is None or abs(r[15]-osp)>0x4000:continue # KickEmu virtual SR is not visible in the trace CCR
  if op in ('lea','pea','jsr','jmp','link','unlk'):continue
  sz={'b':1,'w':2,'l':4}.get(i.mnemonic.split('.')[-1],2)
  if op=='movem':sz*=next(o.register_bits.bit_count() for o in i.operands if o.type==M68K_OP_REG_BITS)
  for index,o in enumerate(i.operands):
   if o.type!=M68K_OP_MEM:continue
   try:a=ea(o,r,pc,sz)
   except ValueError as e:unknown.add((label(pc),str(e),i.mnemonic,i.op_str));continue
   dest=index==len(i.operands)-1
   wr=dest and not (op.startswith('cmp') or op in ('tst','btst','muls','mulu','divs','divu','chk'))
   rd=not (wr and (op in ('move','movem','clr') or (op.startswith('s') and op not in ('sub','subi','subq','subx','swap'))))
   for typ,yes in [('read',rd),('write',wr)]:
    if not yes:continue
    key=(owner,label(pc),typ)
    item=result.setdefault(key,dict(asm=i.mnemonic+' '+i.op_str,addresses=[set() for _ in range(5)],events=0))
    item['events']+=1
    for adr in range(a,a+sz):
     h,off=region(adr);item['addresses'][h].add(off)
    # Track consumers of each byte and writers by caller for follow-on analysis.
    table=reads if typ=='read' else writes
    for adr in range(a,a+sz):
     h,off=region(adr)
     if h<4:table.setdefault(label(adr),set()).add((owner,label(pc)))

summary=[]
for (call,pc,typ),item in result.items():
 item['addresses']=[spans(x) for x in item['addresses']]
 summary.append(dict(call=call,pc=pc,access=typ,**item))
out.write_text(json.dumps(dict(trace_sha256=digest(trace.read_bytes()),fast_sha256=digest(fast.read_bytes()),bases=bases,counts=counts,unknown=list(unknown),accesses=summary,reads={k:sorted(v) for k,v in reads.items()},writes={k:sorted(v) for k,v in writes.items()})))
print('records',len(summary),'unknown',unknown)

if unknown:raise SystemExit(1)
