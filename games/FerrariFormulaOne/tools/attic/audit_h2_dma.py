from pathlib import Path
import sys,json,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
r=Path(__file__).resolve().parents[1];results={}
for tag in ['control','candidate','matched-control','matched-candidate']:
 p=r/f'tmp/step5/c4-q03-render-profile-a1200-fast-h2-{tag}';trace=barto.load(p/'detail.bin');bad=[];counts=collections.Counter();maxaddr=0
 for f in trace.fields:
  for at in range(0,len(f.dma),f.dma_size):
   typ=struct.unpack_from('<h',f.dma,at+29)[0];addr=struct.unpack_from('<I',f.dma,at+12)[0]
   if typ in (3,4,5,6,7,8):
    counts[typ]+=1
    if addr!=0xffffffff:
     maxaddr=max(maxaddr,addr)
     if addr>=0x200000:bad.append((f.index,typ,hex(addr)))
 results[tag]=dict(status='passed' if not bad else 'failed',fields=len(trace.fields),transfers=dict(counts),max_dma_address=hex(maxaddr),bad=bad[:20]);assert not bad,results[tag]
(r/'manifest/render-h2-dma.json').write_text(json.dumps(results,indent=2)+'\n');print(results)
