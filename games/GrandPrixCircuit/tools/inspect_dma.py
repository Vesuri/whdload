import sys,struct,collections,json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p/'trace.bin');m=json.loads((p/'metadata.json').read_text());d=(p/'before.bin').read_bytes();a4=m['data_base']+0x7ffe
print('DMA size',t.fields[0].dma_size,'custom size',len(t.fields[0].custom))
for off in (3648,3652,3672,3676,3590,2044,2048,2052,2056):
 val=struct.unpack_from('>I',d,a4+off-m['base'])[0];print(off,hex(val))
 if off in (3672,3676):
  rp=val;bm=struct.unpack_from('>I',d,rp+4-m['base'])[0];print('bitmap',hex(bm), d[bm-m['base']:bm-m['base']+32].hex())
f=t.fields[0]
for typ in (2,5,6):
 c=collections.Counter(); samples=[]
 for off in range(0,len(f.dma),f.dma_size):
  v=f.dma[off:off+f.dma_size]
  if v[29]!=typ:continue
  c[struct.unpack_from('<H',v)[0]]+=1
  if len(samples)<6:samples.append(bytes(v).hex())
 print('type',typ,'regs',c,'samples',samples)
for f in t.fields[:15]:
 events=[]
 for pc,c,r in t.instructions(f):
  if pc in [m['code_base']+v for v in (0x39e,0x3a2,0xcf04,0x729a,0xc7f4,0x8864,0xce1e)]:events.append((hex(pc-m['code_base']),hex(r[8])))
 print(f.index,events[:35])
