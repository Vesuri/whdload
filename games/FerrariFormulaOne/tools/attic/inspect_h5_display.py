from pathlib import Path
import sys,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path('tmp/dev/tmp/step5/c4-q03-render-profile-a1200-fast-h5-candidate');t=barto.load(p/'detail.bin')
for f in t.fields:
 if f.index not in [1,38,45]:continue
 rows=[]
 for at in range(0,len(f.dma),f.dma_size):
  reg=struct.unpack_from('<H',f.dma,at)[0];a=struct.unpack_from('<I',f.dma,at+12)[0];typ=struct.unpack_from('<h',f.dma,at+29)[0]
  if 0x52c02<=a<=0x52d53 or 0x55452<=a<=0x555a3 or 0x57ca2<=a<=0x57df3:
   if typ==6 or reg&0xff00==0x1100:rows.append((at//f.dma_size,hex(reg),hex(a),typ))
 print(f.index, 'reads', min(x[0] for x in rows if x[3]==6),max(x[0] for x in rows if x[3]==6), 'writes', [x for x in rows if x[3]!=6])
