import sys,json,collections
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import capstone
from capstone import m68k as m
from render_mutations import Snapshot
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('tmp/prof/w6-capacity-a500-full');chunk=root/(sys.argv[2] if len(sys.argv)>2 else 'capacity-0')
meta=json.loads((chunk/'before.json').read_text()); sim,h3=meta['sim'],meta['h3']
irq=json.loads((root/'capacity-costs.json').read_text())['irq_stack']
banks=[dict(base=int(p.stem.split('-')[1],16),size=p.stat().st_size,file=p.name) for p in chunk.glob('memory-*.bin')]
ram=Snapshot(chunk,banks);cs=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_BIG_ENDIAN|capstone.CS_MODE_M68K_000);cs.detail=True
report=json.loads(Path('tmp/prof/w6-list-owner-none-030/heap-inventory.json').read_text())
changed={i for r in report['rows'] for x in r['h3']['ranges'] for i in range(x['start'],x['end'])}
cache={}; active=None; counts=collections.Counter(); unknown=collections.Counter(); calls=0
trace=barto.load(chunk/'trace.bin')
for f in trace.fields:
 for pc,c,regs in trace.instructions(f):
  if pc==sim+0x1098:
   assert active is None; active=(regs[15],collections.Counter(),collections.Counter())
  if active is None or pc in (None,0x7fffffff) or irq[0]<=regs[15]<irq[1]:continue
  sp,hits,miss=active
  assert sp-0x4000<=regs[15]<=sp,(hex(pc),hex(regs[15]),hex(sp))
  if pc not in cache:
   try: cache[pc]=next(cs.disasm(ram.read(pc,22),pc,count=1))
   except (ValueError,StopIteration):cache[pc]=None
  ins=cache[pc]
  if ins is None:miss[(hex(pc-sim),'decode')]+=1;continue
  width=ins.op_size.size or 1
  width*=next((o.register_bits.bit_count() for o in ins.operands if o.type==m.M68K_OP_REG_BITS),1)
  rr=list(regs)
  for op in ins.operands:
   if op.type!=m.M68K_OP_MEM:continue
   mode=op.address_mode; mem=op.mem
   if mode in (16,17):address=op.imm
   elif mode in (3,4,5):
    address=rr[op.reg-1]
    amount=2 if width==1 and op.reg==m.M68K_REG_A7 else width
    if mode==5: address-=amount;rr[op.reg-1]=address
    if mode==4:rr[op.reg-1]+=amount
   elif mode==6:address=rr[mem.base_reg-1]+mem.disp
   elif mode in (7,8,12,13):
    assert not (mem.in_base_reg or mem.in_disp or mem.out_disp)
    index=rr[mem.index_reg-1]
    if mem.index_size==0:index=((index&65535)^32768)-32768
    address=(pc+2 if mode in (12,13) else rr[mem.base_reg-1])+mem.disp+index*(mem.scale or 1)
   elif mode==11:address=pc+2+mem.disp
   else:miss[(hex(pc-sim),ins.mnemonic+' '+ins.op_str)]+=1;continue
   offset=(address&0xffffffff)-h3
   for i in range(max(0,offset),min(0xbd0c,offset+width)):
    if i in changed:hits[(i,pc-sim,ins.mnemonic,ins.op_str)]+=1
  if pc==sim+0x11c8:
   assert regs[15]==sp
   counts.update(hits);unknown.update(miss);calls+=1;active=None
result=dict(capture_sha256=json.loads((root/'entry.json').read_text())['slave_sha256'],comparison_sha256=report['sha256'],chunk=chunk.name,calls=calls,incomplete=active is not None,unknown=[dict(site=k[0],instruction=k[1],count=v) for k,v in unknown.items()],accesses=[dict(offset=hex(k[0]),site=hex(k[1]),mnemonic=k[2],operands=k[3],count=v) for k,v in sorted(counts.items())])
(chunk/'world-operands-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print('calls',calls,'unique changed bytes',len({k[0] for k in counts}),'unknown',unknown)
for (pc,mnemonic,op) in sorted({k[1:] for k in counts}):print(hex(pc),mnemonic,op,[hex(k[0]) for k in counts if k[1]==pc])
