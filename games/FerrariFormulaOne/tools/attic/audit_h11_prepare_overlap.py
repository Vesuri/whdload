from pathlib import Path
import json,gzip,struct,sys,collections,bisect
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);raw=p/'detail.bin';temporary=not raw.exists()
if temporary:raw.write_bytes(gzip.open(str(raw)+'.gz','rb').read())
def read(n):
 q=p/n;return q.read_bytes() if q.exists() else gzip.open(str(q)+'.gz','rb').read()
c=read('canonical.bin');font=struct.unpack_from('>I',c,0x216d8)[0];stride=2*struct.unpack_from('>H',c,0x2178c)[0]
t=barto.load(raw);blits=[];reads=[];cur=None;pos=0
for f in t.fields:
 for a in range(0,len(f.dma),f.dma_size):
  reg=struct.unpack_from('<H',f.dma,a)[0];addr=struct.unpack_from('<I',f.dma,a+12)[0];typ=struct.unpack_from('<h',f.dma,a+29)[0]
  if (reg&0xff00)==0x1100 and addr==0xdff058:
   cur={'start':pos,'end':pos,'reads':[]};blits.append(cur)
  if typ==5 and cur is not None:cur['end']=pos
  if reg==0x1001 and font<=addr<font+stride*8:reads.append((pos,addr))
  pos+=1
starts=[b['start'] for b in blits]
for pos,addr in reads:
 i=bisect.bisect_right(starts,pos)-1
 if i>=0 and pos<blits[i]['end']:blits[i]['reads'].append(addr)
groups=[b['reads'] for b in blits if len(b['reads'])==56]
for group in groups:
 for glyph in range(7):
  col=group[glyph*8]-font;assert 0<=col<stride
  assert group[glyph*8:glyph*8+8]==[font+col+row*stride for row in range(8)]
cpu=json.loads((p/'h11-cpu-audit.json').read_text());assert len(groups)*56==cpu['prepared_font_bytes'] and len(groups)>0
out=dict(status='passed',prepared_glyph_batches_during_active_blit=len(groups),font_bytes_during_active_blit=len(groups)*56,each_batch='Seven groups of eight ascending live-font row reads, matching all preparation instruction reads in h11-cpu-audit.json.',method='CPU byte reads ordered between BLTSIZE launch and final recorded blitter bus access; no CPU-cycle/DMA-clock interpolation.')
(p/'h11-prepare-overlap.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
if temporary:raw.unlink()
