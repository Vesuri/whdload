#!/usr/bin/env python3
"""Which memory the frame code reads that the simulation (SOFT interrupt) writes.
  render_inputs.py TRACE.bin CODE.bin BASE
Decodes executed stores inside the SOFT handler (game:007ee entry to its rte) and loads outside
it (abs.l, d16(An), (An), (An)+, d8(An,Xn) operands; registers from the trace record), then
prints the overlapping byte ranges and the 22-byte car-node field accessors.  Unknown operand
forms are skipped: absence is not proof.  See docs/game.md, "What the renderer reads".
"""
import sys, re, struct, subprocess, os, collections, json; sys.path.insert(0, os.path.dirname(__file__)); import _amigaxdev; from amigaxdev import barto
from amigaxdev.env import tool
from i500_report import regions
from hunk_state import bss_regions
tr, dump, base = sys.argv[1], sys.argv[2], int(sys.argv[3],0)
t=barto.load(tr); code=open(dump,'rb').read()
g=[r for r in regions(code,base,t.chip) if r[2]=='game'][0][0]; G=0x2de08
dis=subprocess.run([tool('objdump'),'-D','-b','binary','-m','m68k:68000',f'--adjust-vma={base}',f'--start-address={g}',f'--stop-address={g+G}',dump],capture_output=True,text=True).stdout
ins={}
for l in dis.splitlines():
  p=l.split('\t')
  if len(p)>=3:
    try: ins[int(p[0].strip().rstrip(':'),16)]=' '.join(p[2:])
    except ValueError: pass
SZ={'b':1,'w':2,'l':4}
STK=(g-0x2000, g)  # the one supervisor stack sits just below hunk 0
ok=lambda a: a<0xdf0000 and not (STK[0]<=a<STK[1])
ea_re=re.compile(r'^(?:(0x[0-9a-f]+)|(-?\d+)?\((a[0-7]|sp)\)\+?|-\((a[0-7]|sp)\)|\((-?\d+),(a[0-7]|sp),([ad][0-7])\.([wl])\))$')
def reg(n): return 15 if n=='sp' else (8 if n[0]=='a' else 0)+int(n[1])
def ea(op, r, n=2):
  m=ea_re.match(op)
  if not m:
    relative=re.fullmatch(r'\((0x[0-9a-f]+),pc(?:,([ad][0-7])\.([wl]))?\)',op)
    if not relative: return None
    x=r[reg(relative[2])] if relative[2] else 0
    if relative[3]=='w': x=struct.unpack('>h',struct.pack('>H',x&0xffff))[0]
    return (int(relative[1],16)+x)&0xffffff
  if m.group(1): return int(m.group(1),16)
  if m.group(3): return (r[reg(m.group(3))]+int(m.group(2) or 0))&0xffffff
  if m.group(4):
    step=2 if n==1 and m.group(4)=='sp' else n
    return (r[reg(m.group(4))]-step)&0xffffff
  b=r[reg(m.group(6))]; x=r[reg(m.group(7))]
  if m.group(8)=='w': x=struct.unpack('>h',struct.pack('>H',x&0xffff))[0]
  return (b+int(m.group(5))+x)&0xffffff
def split(ops):
  out=[];d=0;cur=''
  for ch in ops:
    if ch=='(':d+=1
    if ch==')':d-=1
    if ch==',' and d==0: out.append(cur);cur=''
    else: cur+=ch
  out.append(cur); return out
writes=collections.defaultdict(set); reads=collections.defaultdict(set)
wpc=collections.defaultdict(collections.Counter); rpc=collections.defaultdict(collections.Counter)
cur=None
soft_returns=collections.Counter()
unknown=collections.Counter()
nested=[]
# The window may start inside an interrupt. Ignore its partial prefix until
# the first complete SOFT entry establishes a reliable context.
context_known=False
for f in t.fields:
  for pc,c,r in t.instructions(f):
    if pc is None: continue
    if pc==g+0x7ee and cur is None:
      cur=r[15]; context_known=True; nested=[]
    if not context_known: continue
    if pc in (g+0x9b30,g+0xb29c): nested.append(r[15])
    text=ins.get(pc)
    if text:
      m=re.match(r'(\w+)(?:\.([bwl]))?\s*(.*)',text)
      mn,sz,ops=m.group(1),m.group(2) or 'w',split(m.group(3)) if m.group(3) else []
      if (mn not in ('lea','pea','jsr','jmp','bsr') and not mn.startswith(('b','db'))) or mn in ('btst','bclr','bset','bchg'):
        n=1 if mn in ('btst','bclr','bset','bchg','tas') or mn in ('st','sf','shi','sls','scc','scs','sne','seq','svc','svs','spl','smi','sge','slt','sgt','sle') else SZ.get(sz,2)
        if mn=='movem':
          # The memory operand covers the complete register list.
          register_list=next((o for o in ops if re.fullmatch(r'(?:[ad][0-7]|sp)(?:-(?:[ad][0-7]|sp))?(?:/(?:[ad][0-7]|sp)(?:-(?:[ad][0-7]|sp))?)*',o)), '')
          count=0
          for group in register_list.split('/'):
            if not group: continue
            ends=group.split('-')
            count+=reg(ends[-1])-reg(ends[0])+1
          n*=count
        if cur is not None and not nested and len(ops)>=1 and mn not in ('cmp','cmpi','tst','btst'):
          a=ea(ops[-1].strip(),r,n)
          if a is None and "(" in ops[-1]: unknown[(pc-g,text)]+=1
          if a is not None and ok(a): writes[a-g].add(n); wpc[a-g][(pc-g,text)]+=1
        if cur is None and not nested:
          # Arithmetic and bit operations read their memory destination too.
          srcs=ops[:-1] if mn in ('move','movea','clr') else ops
          if mn=='movem' and ops and not ops[0].startswith(('d','a')): srcs=[ops[0]]
          for o in srcs:
            a=ea(o.strip(),r,n)
            if a is None and "(" in o: unknown[(pc-g,text)]+=1
            if a is not None and ok(a): reads[a-g].add(n); rpc[a-g][(pc-g,text)]+=1
    if code[pc-base:pc-base+2]==b'\x4e\x73':
      if nested and r[15]==nested[-1]: nested.pop()
      elif cur is not None and r[15]==cur:
        soft_returns[pc-g]+=1
        cur=None
print('Complete SOFT returns: '+', '.join('game:%05x × %d'%(pc,n) for pc,n in sorted(soft_returns.items())))
print('Unsupported executed memory operands: %d forms, %d accesses'%(len(unknown),sum(unknown.values())))
for (pc,text),count in unknown.most_common(20): print('  game:%05x × %d: %s'%(pc,count,text))
# byte-level overlap
wb=set(o+i for o,ns in writes.items() for n in ns for i in range(n))
rb={}
for o,ns in reads.items():
  for n in ns:
    for i in range(n): rb[o+i]=1
shared=sorted(o for o in rb if o in wb)
# group into ranges
rngs=[]
for o in shared:
  if rngs and o<=rngs[-1][1]+1: rngs[-1][1]=o
  else: rngs.append([o,o])
print('SOFT writes %d bytes, frame reads %d bytes of tracked RAM (excluding CIA/VBL handlers); shared %d bytes in %d ranges'%(len(wb),len(rb),len(shared),len(rngs)))
for a,b in rngs:
  A=a+g
  name=('game:%05x'%a) if 0<=a<G else ('abs %06x'%A)
  print('%s-%s (%d bytes)'%(name, ('%05x'%b) if 0<=a<G else '%06x'%(b+g), b-a+1))

nodes=bss_regions(code,base,g)['hunk5'][0]+0xe808
print('\nrecord layout (22-byte stride from hunk5:e808), per field offset: writers in SOFT / readers outside it')
fo=collections.defaultdict(lambda:[collections.Counter(),collections.Counter()])
for a in list(writes)+list(reads):
  if nodes-g<=a<nodes-g+33*22:
    k=(a+g-nodes)%22
    if a in wpc: fo[k][0].update({x:1 for x in wpc[a]})
    if a in rpc: fo[k][1].update({x:1 for x in rpc[a]})
for k in sorted(fo):
  w=', '.join('%05x %s'%(p,t) for (p,t),_ in fo[k][0].most_common(3))
  r=', '.join('%05x %s'%(p,t) for (p,t),_ in fo[k][1].most_common(3))
  print('+%2d  W: %s\n     R: %s'%(k,w,r))

if len(sys.argv)>4:
    with open(sys.argv[4],'w') as output:
        json.dump({'game_base':g,'regions':{'game':[g,g+G],**bss_regions(code,base,g)},'soft_returns':dict(soft_returns),'unsupported_memory_operands':[{'pc':pc,'instruction':text,'count':count} for (pc,text),count in unknown.items()],'reads':{str(o):{'sizes':sorted(ns),'pcs':sorted({pc for pc,text in rpc[o]})} for o,ns in reads.items()},'writes':{str(o):{'sizes':sorted(ns),'pcs':sorted({pc for pc,text in wpc[o]})} for o,ns in writes.items()}},output,indent=2)
