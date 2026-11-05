import sys,json,struct,collections
from harness_a import *
from drive import barto
s=Session(sys.argv[1])
try:
 route(s);exp=s.public_main_base-0x5000;s.input('JOY2_UP',1);advance(s,300)
 p=s.out/'race.bin';s.cmd(f'monitor profile 99 "" "{p}"',timeout=120);t=barto.load(str(p));counts=collections.Counter();dma=[]
 ranges=[(0,0x400,'vectors'),(0x400,0x467c,'fixed low interfaces/data'),(0x467c,0xda7e,'low graphics assets'),(0xda7e,0x11a7e,'Chip graphics scratch/background'),(0x11a7e,0x19a7e,'audio Chip storage'),(0x19a7e,0x6f780,'graphics assets'),(0x6f780,0x80000,'screens/staging'),(0x80000,0xbc3ec,'old main image'),(0xbc3ec,0x100000,'graphics heap')]
 for f in t.fields:
  for i in range(0,len(f.dma),f.dma_size):
   a=struct.unpack_from('<I',f.dma,i+12)[0];kind=struct.unpack_from('<h',f.dma,i+29)[0]
   if kind==2:
    for lo,hi,label in ranges:
     if lo<=a<hi:counts[label]+=1;break
   elif kind!=0 and exp<=a<exp+0x65000:dma.append([a,kind])
 assert not dma,dma[:20]
 (s.out/'bus.json').write_text(json.dumps(dict(fields=len(t.fields),chip_cpu_bus_records=dict(counts),public_dma_reads=dma,expansion_base=hex(exp),expansion_bytes=0x65000),indent=2));print(dict(counts),flush=True)
finally:s.quit()
