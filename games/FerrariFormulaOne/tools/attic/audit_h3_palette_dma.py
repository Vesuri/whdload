from pathlib import Path
import gzip,sys,struct,collections,json
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
r=Path(__file__).resolve().parents[1];results={}
for arm in ['control','candidate']:
 p=r/f'tmp/step5/c4-q03-render-profile-a1200-fast-h3-matched-{arm}';f=p/'detail.bin';f.write_bytes(gzip.decompress((p/'detail.bin.gz').read_bytes()));t=barto.load(f);rows=[]
 for field in t.fields:
  for at in range(0,len(field.dma),field.dma_size):
   reg=struct.unpack_from('<H',field.dma,at)[0];typ=struct.unpack_from('<h',field.dma,at+29)[0]
   if reg!=65535 and 0x180<=(reg&0x1fe)<=0x1be:
    rows.append((field.index,at//field.dma_size,typ,reg,struct.unpack_from('<Q',field.dma,at+2)[0]))
 results[arm]=rows;f.unlink();print(arm,collections.Counter((x[2],hex(x[3]),x[4]) for x in rows).most_common(12))
(r/'manifest/render-h3-palette-dma.json').write_text(json.dumps(results,indent=2)+'\n')
