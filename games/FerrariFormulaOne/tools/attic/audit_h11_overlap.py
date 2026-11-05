from pathlib import Path
import sys,json,struct,gzip,shutil,bisect,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1])
def read(n):
 f=p/n
 return f.read_bytes() if f.exists() else gzip.open(str(f)+'.gz','rb').read()
m=read('start.bin');m+=bytes(0x200000-len(m))+read('start-fast.bin');c=read('canonical.bin');u=lambda a:struct.unpack_from('>I',m,a)[0]
tables=[struct.unpack_from('>I',c,a)[0] for a in [0x226ae,0x226b2]];planes=[u(a+4*i) for a in tables for i in range(3)];assert len(set(planes))==6
clock={a+y*48+x for a in planes for y in range(24,32) for x in range(32,42)}
raw=p/'detail.bin';temporary=not raw.exists()
if temporary:
 with gzip.open(str(raw)+'.gz','rb') as a,raw.open('wb') as b:shutil.copyfileobj(a,b)
t=barto.load(raw);blits=[];writes=[];pos=0;cur=None;hist=collections.Counter()
for f in t.fields:
 for at in range(0,len(f.dma),f.dma_size):
  reg=struct.unpack_from('<H',f.dma,at)[0];dat=struct.unpack_from('<Q',f.dma,at+2)[0];addr=struct.unpack_from('<I',f.dma,at+12)[0];typ=struct.unpack_from('<h',f.dma,at+29)[0]
  if (reg&0xff00)==0x1100 and addr==0xdff058:
   cur={'start':pos,'end':pos,'clock_access':False};blits.append(cur)
  if typ==5 and cur is not None:
   cur['end']=pos
   if addr in clock or addr+1 in clock:cur['clock_access']=True
  if reg==0x1101 and addr in clock:writes.append((pos,addr))
  pos+=1
starts=[b['start'] for b in blits];concurrent=0
for pos,addr in writes:
 i=bisect.bisect_right(starts,pos)-1
 if i>=0 and pos<blits[i]['end']:
  concurrent+=1;assert not blits[i]['clock_access'],(pos,addr,blits[i])
out=dict(status='passed',clock_byte_writes=len(writes),clock_writes_during_active_blit=concurrent,blits=len(blits),clock_rows=[24,31],clock_byte_columns=[32,41],disjoint_blitter_accesses=True,scope='Both live pointer views, all recorded blitter bus accesses; bounded diagnostic observation, not a proof for every native layout.')
assert len(writes)>0
(p/'h11-overlap-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
if temporary:raw.unlink()
