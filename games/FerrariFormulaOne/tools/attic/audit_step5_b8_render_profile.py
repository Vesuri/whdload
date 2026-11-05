from pathlib import Path
import sys,json,struct,hashlib,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1]
a=barto.load(p/'detail-raw.bin');b=barto.load(p/'detail.bin');assert len(a.fields)==len(b.fields);count=0
for af,bf in zip(a.fields,b.fields):
 assert af.cycles==bf.cycles and af.custom==bf.custom and af.dma==bf.dma
 ai=list(a.instructions(af));bi=list(b.instructions(bf));assert len(ai)==len(bi)
 for x,y in zip(ai,bi):assert x[1:]==y[1:];count+=1
j=json.loads((p/'profile.json').read_text());per=json.loads((p/'percar.json').read_text());cls=json.loads((p/'classified.json').read_text());debt=json.loads((p/'debt.json').read_text());cycles=j['per_update_cycles'];mean=sum(cycles)/len(cycles)
assert abs(sum(per['segment_totals_exact'].values())-mean)<1e-8
assert abs(sum(cls['totals'].values())-mean)<1e-8
# save_custom writes a 4-byte chipset prefix then big-endian custom registers.
# Audit live copper, enabled bitplanes, and enabled blitter channels. Audio
# hunk placement is covered by the matrix; save_custom omits audio pointers.
pointers=[];dma=collections.Counter();bad=[]
for f in a.fields:
 u16=lambda at:struct.unpack_from('>H',f.custom,4+at)[0]
 u32=lambda at:struct.unpack_from('>I',f.custom,4+at)[0]
 for label,addr in [('copper1',u32(0x80)),('copper2',u32(0x84))]+[(f'bitplane{i}',u32(0xe0+4*i)) for i in range((u16(0x100)>>12)&7)]:
  pointers.append((label,addr))
  if addr>=0x80000:bad.append((f.index,label,hex(addr)))
 for i,at in enumerate((0x50,0x4c,0x48,0x54)):
  # In line mode APT is the signed error accumulator and B uses BLTBDAT.
  # Audit actual DMA addresses independently below, including line transfers.
  if (u16(0x42)&1) and i<2:continue
  if u16(0x40)&(0x800>>i):
   ptr=u32(at);pointers.append((f'blitter{i}',ptr))
   if ptr>=0x80000:bad.append((f.index,f'blitter{i}',hex(ptr)))
 for at in range(0,len(f.dma),f.dma_size):
  typ=struct.unpack_from('<h',f.dma,at+29)[0];addr=struct.unpack_from('<I',f.dma,at+12)[0]
  if typ in (3,4,5,6,7,8):
   dma[typ]+=1
   if addr!=0xffffffff and addr>=0x80000:bad.append((f.index,typ,hex(addr)))
report=dict(status='passed' if not bad else 'failed',mean_cycles=mean,worst_five=max(sum(cycles[i:i+5])/5 for i in range(len(cycles)-4)),peak=max(cycles),cycle_gate_applies=False,cycle_gate_scope='Full drawing trace: logic gates are evaluated in the matched control profile; presentation is gated by the untraced FPS capture.',normalization=dict(instructions_checked=count,all_costs_and_registers_unchanged=True),analyzer_totals_agree=True,dma=dict(fields=len(a.fields),transfer_counts=dict(dma),pointer_min=min(x[1] for x in pointers),pointer_max=max(x[1] for x in pointers),bad=bad[:30],scope='Full native drawing trace with active blitter, bitplane, copper and sprite DMA. Audio hunk is Chip in all four profile matrices.'))
(p/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['status']=='passed'
