from pathlib import Path
import sys,struct,json
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5/c4-divide-r3a-fullloop-a500-candidate';t=barto.load(p/'detail-raw.bin');f=t.fields[29]
u16=lambda off:struct.unpack_from('>H',f.custom,4+off)[0]
u32=lambda off:struct.unpack_from('>I',f.custom,4+off)[0]
assert u16(2)==0x7fb and not u16(2)&0x4000 and u16(0x42)==0 and u32(0x50)==0xffd4fffe
rows=list(t.instructions(f));assert rows[0][0]==0xce8722
slow=(p/'start-raw-slow.bin').read_bytes();assert slow[0xce8722-0xc00000:0xce8728-0xc00000]==bytes.fromhex('2368000c0050')
ptr=struct.unpack_from('>I',slow,rows[0][2][8]+12-0xc00000)[0];assert ptr==0xcf38
start=next(i for i,(pc,_,__) in enumerate(rows) if pc==0xce873e);assert start==492
assert slow[0xce873e-0xc00000:0xce8742-0xc00000]==bytes.fromhex('33400058')
for field in t.fields:
 for at in range(0,len(field.dma),field.dma_size):
  typ=struct.unpack_from('<h',field.dma,at+29)[0];addr=struct.unpack_from('<I',field.dma,at+12)[0]
  if typ in (3,4,5,6,7,8):assert addr==0xffffffff or addr<0x80000
out=dict(status='passed',trace=p.name,field=29,idle_dmaconr=hex(u16(2)),stale_line_accumulator=hex(u32(0x50)),next_instruction='move.l $c(a0),$50(a1)',new_chip_pointer=hex(ptr),first_bltsize_instruction_index=start,all_recorded_dma_chip=True,conclusion='Snapshot falls between native line-to-area register setup writes. BLTAPT is stale while idle; it is replaced before BLTSIZE. Enabled channel bits alone do not imply live DMA.')
(r/'manifest/step5-c4-r3a-idle-pointer.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
